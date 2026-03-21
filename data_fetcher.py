"""
Data Fetcher v3.3
Fixes vs previous:
  - prev_close: replaced 'or' chaining (skipped valid 0.0) with explicit None check
  - sector_mom division by zero: closes[-20] == 0 guard
  - fetch_sector_correlation division by zero: closes[i-1] == 0 guard
  - datetime.utcnow() → datetime.now(timezone.utc) (Python 3.12)
  - fetch_indices parallelised with ThreadPoolExecutor (was sequential, slow cold start)
  - rs_rank computed in _sector_agg so top_gainers/top_losers have correct rank
  - process_stock called from fetch_breadth_universe now passes earnings list
  - Removed unused import: threading
"""

import time, math, requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from nifty_indices import NIFTY_INDICES, SECTORS, get_all_stocks
from technical_indicators import (
    calculate_rsi, calculate_ema, calculate_sma, calculate_dma_status,
    calculate_momentum_score, calculate_volume_ratio, calculate_volume_profile,
    calculate_relative_strength, calculate_rrg_values, get_rrg_quadrant,
    validate_minervini_template, calculate_rs_rank, assign_grade, safe_avg,
    calculate_atr_pct,
    detect_nr7, detect_nr4, detect_vcp, detect_pocket_pivot, detect_rs_divergence,
    calculate_advance_decline, count_new_highs_lows, calculate_pct_above_ma,
    calculate_correlation_matrix, check_price_continuity,
)
from watchlist import init_db, record_rrg_snapshot

init_db()

YAHOO_BASE  = "https://query1.finance.yahoo.com/v8/finance/chart"
NSE_BASE    = "https://www.nseindia.com/api"
YH_HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
NSE_HEADERS = {
    "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "en-US,en;q=0.9",
    "Referer":          "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}

_nse_session   = requests.Session()
_nse_session.headers.update(NSE_HEADERS)
_nse_cookie_ts = 0.0


def _refresh_nse_session():
    global _nse_cookie_ts
    if time.time() - _nse_cookie_ts < 3600:
        return
    try:
        _nse_session.get("https://www.nseindia.com", timeout=8)
        _nse_cookie_ts = time.time()
    except Exception:
        pass


# ── Yahoo Finance fetch ───────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_chart(symbol: str, range_: str = "6mo", interval: str = "1d") -> dict:
    """
    Single v8 chart fetch. Returns {ohlcv, meta} or {ohlcv:[], meta:None}.
    Bug fixed: OHLCV arrays extracted once before loop (was O(n²) per-bar).
    Bug fixed: prev_close uses explicit None check, not 'or' (skipped valid 0.0).
    """
    url = (f"{YAHOO_BASE}/{requests.utils.quote(symbol)}"
           f"?range={range_}&interval={interval}&includePrePost=false")
    try:
        r = requests.get(url, headers=YH_HEADERS, timeout=10)
        r.raise_for_status()
        data   = r.json()
        result = ((data.get("chart") or {}).get("result") or [None])[0]
        if not result:
            return {"ohlcv": [], "meta": None}

        m = result.get("meta") or {}
        # Bug fixed: prev_close must use is-None check, not 'or', because 0.0 is valid
        prev_c = m.get("previousClose")
        if prev_c is None:
            prev_c = m.get("chartPreviousClose")
        if prev_c is None:
            prev_c = 0.0

        meta = {
            "symbol":       m.get("symbol", symbol),
            "short_name":   m.get("shortName", symbol),
            "price":        float(m.get("regularMarketPrice")  or 0),
            "prev_close":   float(prev_c),
            "volume":       int(m.get("regularMarketVolume")   or 0),
            "day_high":     float(m.get("regularMarketDayHigh") or 0),
            "day_low":      float(m.get("regularMarketDayLow")  or 0),
            "week52_high":  float(m.get("fiftyTwoWeekHigh")    or 0),
            "week52_low":   float(m.get("fiftyTwoWeekLow")     or 0),
            "avg_volume_3m":int(m.get("averageDailyVolume3Month") or 0),
            "exchange_tz":  m.get("exchangeTimezoneName", "Asia/Kolkata"),
        }

        ts          = result.get("timestamp") or []
        q           = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes_raw  = q.get("close")  or []
        opens_raw   = q.get("open")   or []
        highs_raw   = q.get("high")   or []
        lows_raw    = q.get("low")    or []
        volumes_raw = q.get("volume") or []

        ohlcv = []
        for i, t in enumerate(ts):
            c = closes_raw[i] if i < len(closes_raw) else None
            o = opens_raw[i]  if i < len(opens_raw)  else None
            if c is None or o is None:
                continue
            ohlcv.append({
                "date":   time.strftime("%Y-%m-%d", time.gmtime(t)),
                "open":   float(o or 0),
                "high":   float(highs_raw[i]   if i < len(highs_raw)   else 0),
                "low":    float(lows_raw[i]    if i < len(lows_raw)    else 0),
                "close":  float(c or 0),
                "volume": int(volumes_raw[i]   if i < len(volumes_raw) else 0),
            })
        return {"ohlcv": ohlcv, "meta": meta}
    except Exception:
        return {"ohlcv": [], "meta": None}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_chart_nse_fallback(symbol: str, range_: str = "6mo") -> dict:
    """Yahoo first; NSE quote API fallback for delisted / missing symbols."""
    result = fetch_chart(symbol, range_)
    if result["ohlcv"]:
        return result
    _refresh_nse_session()
    clean = symbol.replace(".NS","").replace("-","%2D").replace("&","%26")
    try:
        r = _nse_session.get(f"{NSE_BASE}/quote-equity?symbol={clean}", timeout=8)
        if r.status_code == 200:
            d   = r.json()
            pd_ = d.get("priceInfo") or {}
            prev_nse = pd_.get("previousClose")
            if prev_nse is None:
                prev_nse = 0.0
            return {"ohlcv": [], "meta": {
                "symbol":       symbol,
                "short_name":   (d.get("info") or {}).get("companyName", symbol),
                "price":        float(pd_.get("lastPrice")     or 0),
                "prev_close":   float(prev_nse),
                "volume":       int((d.get("marketDeptOrderBook") or {})
                                    .get("tradeInfo", {}).get("totalTradedVolume", 0)),
                "day_high":     float((pd_.get("intraDayHighLow") or {}).get("max") or 0),
                "day_low":      float((pd_.get("intraDayHighLow") or {}).get("min") or 0),
                "week52_high":  float((pd_.get("weekHighLow")    or {}).get("max") or 0),
                "week52_low":   float((pd_.get("weekHighLow")    or {}).get("min") or 0),
                "avg_volume_3m": 0,
                "exchange_tz":  "Asia/Kolkata",
                "nse_fallback": True,
            }}
    except Exception:
        pass
    return {"ohlcv": [], "meta": None}


# ── Market hours ──────────────────────────────────────────────────────────────

def is_market_open() -> bool:
    """NSE: Mon–Fri 09:15–15:30 IST."""
    # Bug fixed: datetime.utcnow() deprecated → timezone-aware
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    if now_ist.weekday() >= 5:
        return False
    ot = now_ist.replace(hour=9,  minute=15, second=0, microsecond=0)
    ct = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return ot <= now_ist <= ct


# ── FII / DII ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fii_dii() -> list:
    """Returns oldest-first list of up to 30 trading days of FII/DII data."""
    _refresh_nse_session()
    try:
        r = _nse_session.get(f"{NSE_BASE}/fiidiiTradeReact", timeout=10)
        if r.status_code != 200:
            return _synthetic_fii_dii()
        rows, result = r.json(), []
        for row in rows:
            try:
                def to_f(k): return float(str(row.get(k, "0")).replace(",", "") or 0)
                result.append({
                    "date":     row.get("date", ""),
                    "fii_net":  to_f("fiiNet"),  "dii_net":  to_f("diiNet"),
                    "fii_buy":  to_f("fiiBuy"),  "fii_sell": to_f("fiiSell"),
                    "dii_buy":  to_f("diiBuy"),  "dii_sell": to_f("diiSell"),
                })
            except Exception:
                continue
        # NSE returns newest-first → take 30 most recent → reverse to oldest-first
        return list(reversed(result[:30])) if result else _synthetic_fii_dii()
    except Exception:
        return _synthetic_fii_dii()


def _synthetic_fii_dii() -> list:
    import random; random.seed(42)
    base = datetime.now(timezone.utc)
    rows = []
    for i in range(30):
        d = base - timedelta(days=i)
        if d.weekday() < 5:
            fii = random.uniform(-3000, 3000); dii = random.uniform(-1000, 2000)
            rows.append({
                "date": d.strftime("%d-%b-%Y"), "fii_net": fii, "dii_net": dii,
                "fii_buy": abs(fii)+1000, "fii_sell": abs(fii),
                "dii_buy": abs(dii)+500,  "dii_sell": abs(dii),
                "_synthetic": True,
            })
    return rows[::-1]


# ── Earnings calendar ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_upcoming_earnings() -> List[str]:
    _refresh_nse_session()
    try:
        today  = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        fmt    = "%d-%m-%Y"
        params = {"index": "equities",
                  "from_date": today.strftime(fmt),
                  "to_date":   (today + timedelta(days=7)).strftime(fmt)}
        r = _nse_session.get(f"{NSE_BASE}/corporate-actions", params=params, timeout=10)
        if r.status_code != 200:
            return []
        data    = r.json() if isinstance(r.json(), list) else (r.json().get("data") or [])
        symbols = set()
        for row in data:
            purpose = (row.get("purpose") or row.get("subject") or "").lower()
            if any(kw in purpose for kw in ["results", "quarterly", "financial"]):
                sym = row.get("symbol", "")
                if sym: symbols.add(sym + ".NS")
        return list(symbols)
    except Exception:
        return []


# ── Process single stock ──────────────────────────────────────────────────────

def process_stock(symbol: str, bench_ohlcv: list,
                  sector_name: str = "Unknown",
                  earnings_symbols: list = None) -> Optional[dict]:
    res   = fetch_chart_nse_fallback(symbol, "6mo")
    ohlcv = res["ohlcv"]; meta = res["meta"]
    if len(ohlcv) < 20 or not meta:
        return None

    bad_bars = check_price_continuity(ohlcv)
    closes   = [d["close"]  for d in ohlcv]
    volumes  = [d["volume"] for d in ohlcv]

    rsi_arr = calculate_rsi(closes)
    ema5    = calculate_ema(closes, 5);  ema10 = calculate_ema(closes, 10)
    ema21   = calculate_ema(closes, 21); ema50 = calculate_ema(closes, 50)
    dma     = calculate_dma_status(closes)
    atr_pct = calculate_atr_pct(ohlcv)

    nr7 = detect_nr7(ohlcv); nr4 = detect_nr4(ohlcv)
    vcp = detect_vcp(ohlcv); pp  = detect_pocket_pivot(ohlcv)
    rsd = (detect_rs_divergence(ohlcv, bench_ohlcv)
           if len(bench_ohlcv) >= 20 else [False] * len(ohlcv))

    mom  = calculate_momentum_score(ohlcv)
    volr = calculate_volume_ratio(volumes)
    bc   = [d["close"] for d in bench_ohlcv]
    rs   = calculate_relative_strength(closes, bc)
    rrg  = calculate_rrg_values(closes, bc)
    quad = get_rrg_quadrant(rrg["rs_ratio"], rrg["rs_momentum"])

    minervini = validate_minervini_template(ohlcv)
    vp        = calculate_volume_profile(ohlcv[-60:], bins=22)

    price   = meta["price"]
    prev    = meta["prev_close"]
    change  = price - prev
    chg_pct = change / prev * 100 if prev and prev != 0 else 0.0

    has_earnings = bool(earnings_symbols) and (symbol in earnings_symbols)

    return {
        "symbol":     symbol, "name": meta["short_name"], "sector": sector_name,
        "price":      price,  "change": change,           "change_pct": chg_pct,
        "volume":     meta["volume"], "avg_volume": meta["avg_volume_3m"],
        "high52w":    meta["week52_high"], "low52w": meta["week52_low"],
        "rsi":        rsi_arr[-1],
        "ema5":       ema5[-1],  "ema10": ema10[-1],
        "ema21":      ema21[-1], "ema50": ema50[-1],
        "dma20":      dma["dma20"], "dma50": dma["dma50"], "dma200": dma["dma200"],
        "above20dma": dma["above20"], "above50dma": dma["above50"], "above200dma": dma["above200"],
        "is_nr7":     nr7[-1], "is_nr4": nr4[-1],
        "is_vcp":     vcp[-1], "is_pocket_pivot": pp[-1],
        "is_rs_div":  rsd[-1] if rsd else False,
        "momentum":   mom, "vol_ratio": volr, "rs": rs, "atr_pct": atr_pct,
        "rs_ratio":   rrg["rs_ratio"], "rs_momentum": rrg["rs_momentum"],
        "rrg_quadrant": quad,
        "rs_rank":    50,  # filled post-processing in callers
        "minervini_passes":       minervini["passes"],
        "minervini_criteria_met": minervini.get("criteria_met", 0),
        "minervini_detail":       minervini,
        "volume_profile": vp,
        "has_earnings":   has_earnings,
        "data_gap":       len(bad_bars) > 0,
        "nse_fallback":   meta.get("nse_fallback", False),
        "ohlcv":          ohlcv[-60:],
    }


# ── Sector aggregation ────────────────────────────────────────────────────────

def _sector_agg(stocks: list, bench_c: list, sector: dict) -> dict:
    """
    Aggregates sector-level metrics.
    Bug fixed: rs_rank now computed here so top_gainers/top_losers carry correct rank.
    Uses safe_avg() to handle any NaN RSI/momentum values.
    """
    # Compute RS rank within this sector
    rs_scores = [s["rs"] for s in stocks]
    ranks = calculate_rs_rank(rs_scores)
    for s, rk in zip(stocks, ranks):
        s["rs_rank"] = rk

    def sa(k): return safe_avg([s.get(k, 0) for s in stocks])
    breadth  = sum(1 for s in stocks if s["above20dma"]) / max(1, len(stocks)) * 100
    sh       = fetch_chart(sector["index_symbol"], "6mo")["ohlcv"]
    rrg      = (calculate_rrg_values([d["close"] for d in sh], bench_c) if sh
                else {"rs_ratio": 100, "rs_momentum": 100})
    record_rrg_snapshot(sector["name"], rrg["rs_ratio"], rrg["rs_momentum"])
    sorted_s = sorted(stocks, key=lambda s: s["change_pct"], reverse=True)
    return {
        "name":         sector["name"],
        "color":        sector["color"],
        "index_symbol": sector.get("index_symbol", ""),
        "change":       sa("change_pct"),
        "rsi":          sa("rsi"),
        "momentum":     sa("momentum"),
        "breadth":      breadth,
        "vol_ratio":    sa("vol_ratio"),
        "rs_ratio":     rrg["rs_ratio"],
        "rs_momentum":  rrg["rs_momentum"],
        "rrg_quadrant": get_rrg_quadrant(rrg["rs_ratio"], rrg["rs_momentum"]),
        "top_gainers":  sorted_s[:3],
        "top_losers":   sorted_s[-3:][::-1],
        "stock_count":  len(sector["stocks"]),
    }


def _empty_sector(sector: dict) -> dict:
    return {
        "name": sector["name"], "color": sector["color"],
        "index_symbol": sector["index_symbol"],
        "change": 0, "rsi": 50, "momentum": 50, "breadth": 0, "vol_ratio": 1,
        "rs_ratio": 100, "rs_momentum": 100, "rrg_quadrant": "Lagging",
        "top_gainers": [], "top_losers": [], "stock_count": len(sector["stocks"]),
    }


# ── Public fetch functions ────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sector_data(sector_name: str) -> Optional[dict]:
    sector = next((s for s in SECTORS if s["name"] == sector_name), None)
    if not sector: return None
    bench    = fetch_chart("^NSEI", "6mo")["ohlcv"]
    bench_c  = [d["close"] for d in bench]
    earnings = fetch_upcoming_earnings()
    stocks   = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(process_stock, s["symbol"], bench, sector_name, earnings): s
                for s in sector["stocks"]}
        for f in as_completed(futs):
            try:
                r = f.result()
                if r: stocks.append(r)
            except Exception: pass
    if not stocks: return None
    result = _sector_agg(stocks, bench_c, sector)
    result["stocks"]     = stocks
    result["industries"] = list(dict.fromkeys(s["industry"] for s in sector["stocks"]))
    return result


@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_sectors() -> list:
    """Single flat ThreadPool for all 95 stocks (no nested pools)."""
    bench    = fetch_chart("^NSEI", "6mo")["ohlcv"]
    bench_c  = [d["close"] for d in bench]
    earnings = fetch_upcoming_earnings()
    stock_by_sector = {sect["name"]: [] for sect in SECTORS}

    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {
            pool.submit(process_stock, s["symbol"], bench, sect["name"], earnings): sect["name"]
            for sect in SECTORS for s in sect["stocks"]
        }
        for f in as_completed(futs):
            try:
                r = f.result()
                if r: stock_by_sector[r["sector"]].append(r)
            except Exception: pass

    results = []
    for sector in SECTORS:
        stocks = stock_by_sector.get(sector["name"], [])
        results.append(_sector_agg(stocks, bench_c, sector) if stocks else _empty_sector(sector))

    order = {s["name"]: i for i, s in enumerate(SECTORS)}
    return sorted(results, key=lambda r: order.get(r["name"], 99))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_indices() -> list:
    """
    Bug fixed: was sequential (15 HTTP calls one-by-one on cold start).
    Now parallelised with ThreadPoolExecutor.
    """
    items = list(NIFTY_INDICES.items())
    results = []

    def _fetch_index(name_sym):
        name, sym = name_sym
        res   = fetch_chart(sym, "3mo")
        ohlcv = res["ohlcv"]; meta = res["meta"]
        if not meta: return None
        closes  = [d["close"] for d in ohlcv]
        rsi_arr = calculate_rsi(closes)
        prev    = meta["prev_close"]
        price   = meta["price"]
        return {
            "name":       name, "symbol": sym,
            "price":      price,
            "change":     price - prev,
            "change_pct": (price - prev) / prev * 100 if prev and prev != 0 else 0.0,
            "rsi":        rsi_arr[-1] if rsi_arr else float("nan"),
            "volume":     meta["volume"],
            "week52_high": meta.get("week52_high", 0),
            "week52_low":  meta.get("week52_low",  0),
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(_fetch_index, item): item for item in items}
        for f in as_completed(futs):
            try:
                r = f.result()
                if r: results.append(r)
            except Exception: pass

    # Preserve NIFTY_INDICES order
    order = {sym: i for i, (_, sym) in enumerate(items)}
    return sorted(results, key=lambda r: order.get(r["symbol"], 99))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_screener_raw(rsi_min=0, rsi_max=100, momentum_min=0, volume_breakout=False,
                       pattern="all", rrg_quadrant="all", dma_filter="all",
                       minervini_only=False) -> list:
    """
    Pure cached function — NO side effects (alerts/breadth).
    Side effects are handled in fetch_screener() wrapper.
    """
    bench    = fetch_chart("^NSEI", "6mo")["ohlcv"]
    earnings = fetch_upcoming_earnings()

    sector_mom = {}
    for sec in SECTORS:
        sh     = fetch_chart(sec["index_symbol"], "3mo")["ohlcv"]
        closes = [d["close"] for d in sh]
        if len(closes) >= 20 and closes[-20] and closes[-20] != 0:  # Bug fixed: /0 guard
            sector_mom[sec["name"]] = 50 + (closes[-1] - closes[-20]) / closes[-20] * 100
        else:
            sector_mom[sec["name"]] = 50.0

    all_cfg = get_all_stocks()
    stocks  = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(process_stock, s["symbol"], bench, s["sector"], earnings): s
                for s in all_cfg}
        for f in as_completed(futs):
            try:
                r = f.result()
                if r: stocks.append(r)
            except Exception: pass

    ranks = calculate_rs_rank([s["rs"] for s in stocks])
    for s, rk in zip(stocks, ranks):
        s["rs_rank"] = rk

    for s in stocks:
        ss = sector_mom.get(s["sector"], 50.0)
        g  = assign_grade(ss, s["momentum"], s["rs_rank"])
        s["grade"] = g["grade"]; s["grade_desc"] = g["description"]

    def passes(s):
        rsi = s.get("rsi") or 0
        if isinstance(rsi, float) and math.isnan(rsi): rsi = 0
        if not (rsi_min <= rsi <= rsi_max):          return False
        if s["momentum"] < momentum_min:             return False
        if volume_breakout and (s.get("vol_ratio") or 0) <= 1.5: return False
        if minervini_only  and not s["minervini_passes"]:         return False
        if pattern == "nr7"         and not s["is_nr7"]:           return False
        if pattern == "nr4"         and not s["is_nr4"]:           return False
        if pattern == "vcp"         and not s["is_vcp"]:           return False
        if pattern == "pocketpivot" and not s["is_pocket_pivot"]:  return False
        if pattern == "rsdiv"       and not s["is_rs_div"]:        return False
        if pattern == "minervini"   and not s["minervini_passes"]: return False
        if rrg_quadrant != "all"    and s["rrg_quadrant"] != rrg_quadrant: return False
        if dma_filter == "above20"  and not s["above20dma"]:  return False
        if dma_filter == "above50"  and not s["above50dma"]:  return False
        if dma_filter == "above200" and not s["above200dma"]: return False
        if dma_filter == "allAbove" and not (s["above20dma"] and s["above50dma"]
                                             and s["above200dma"]): return False
        return True

    return [s for s in stocks if passes(s)]


def fetch_screener(**kwargs) -> list:
    """Wrapper: calls pure cached fetch_screener_raw, then fires side effects."""
    results = fetch_screener_raw(**kwargs)
    _run_side_effects(results)
    return results


def _run_side_effects(stocks: list):
    from watchlist import evaluate_alerts, record_breadth
    evaluate_alerts(stocks)
    ad  = calculate_advance_decline(stocks)
    hl  = count_new_highs_lows(stocks)
    pma = calculate_pct_above_ma(stocks)
    record_breadth(ad["advances"], ad["declines"],
                   hl["new_highs"], hl["new_lows"],
                   pma["above_20dma"], pma["above_50dma"])


@st.cache_data(ttl=60, show_spinner=False)
def fetch_breadth_universe() -> dict:
    """Independent universe fetch for the Breadth tab."""
    bench    = fetch_chart("^NSEI", "6mo")["ohlcv"]
    earnings = fetch_upcoming_earnings()   # Bug fixed: was not passing earnings
    stocks   = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(process_stock, s["symbol"], bench, s["sector"], earnings): s
                for s in get_all_stocks()}
        for f in as_completed(futs):
            try:
                r = f.result()
                if r: stocks.append(r)
            except Exception: pass
    ad  = calculate_advance_decline(stocks)
    hl  = count_new_highs_lows(stocks)
    pma = calculate_pct_above_ma(stocks)
    return {"stocks": stocks, "ad": ad, "hl": hl, "pma": pma}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_sector_correlation() -> dict:
    """30-day return correlation matrix across all sector indices."""
    returns = {}
    for sec in SECTORS:
        sh     = fetch_chart(sec["index_symbol"], "3mo")["ohlcv"]
        if len(sh) < 5: continue
        closes = [d["close"] for d in sh]
        # Bug fixed: guard division by zero when close[i-1] == 0
        rets   = [(closes[i] - closes[i-1]) / closes[i-1]
                  for i in range(1, len(closes)) if closes[i-1] != 0]
        returns[sec["name"]] = rets
    return calculate_correlation_matrix(returns, window=30)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_watchlist_stocks() -> list:
    from watchlist import get_watchlist_symbols
    symbols = get_watchlist_symbols()
    if not symbols: return []
    bench    = fetch_chart("^NSEI", "6mo")["ohlcv"]
    earnings = fetch_upcoming_earnings()
    stocks   = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(process_stock, sym, bench, "Unknown", earnings): sym
                for sym in symbols}
        for f in as_completed(futs):
            try:
                r = f.result()
                if r: stocks.append(r)
            except Exception: pass
    return stocks
