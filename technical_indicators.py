"""
Technical Indicators v3.1 — Bug-fixed + ATR added
Fixes:
  - sma_series removed from dma_status return (memory waste, never used)
  - RRG NaN-fill-with-0 → forward-fill (was corrupting RS-Momentum SMA)
  - Minervini threshold 210→100 bars (always failed on 6mo/126-bar data)
  - calculate_sma uses O(n) rolling sum (was O(n²) per-bar slicing)
  - VCP: bar i now included in week-0 range
  - correlation sqrt guarded against negative (floating-point -ε)
  - advance_decline: guards None change_pct
New:
  - calculate_atr() / calculate_atr_pct() — position sizing & NR context
  - safe_avg() — NaN-safe average helper
"""

import math
from typing import List, Dict, Optional


def safe_avg(values: List[float]) -> float:
    valid = [v for v in values if v is not None and not (isinstance(v,float) and math.isnan(v))]
    return sum(valid) / len(valid) if valid else 0.0


# ── Moving averages ───────────────────────────────────────────────────────────

def calculate_sma(data: List[float], period: int) -> List[float]:
    """O(n) rolling-sum — was O(n²) slice per bar."""
    n = len(data)
    result = [float("nan")] * n
    if n < period:
        return result
    ws = sum(data[:period])
    result[period - 1] = ws / period
    for i in range(period, n):
        ws += data[i] - data[i - period]
        result[i] = ws / period
    return result


def calculate_ema(data: List[float], period: int) -> List[float]:
    result = [float("nan")] * len(data)
    if len(data) < period:
        return result
    mult = 2.0 / (period + 1)
    ema  = sum(data[:period]) / period
    result[period - 1] = ema
    for i in range(period, len(data)):
        ema = (data[i] - ema) * mult + ema
        result[i] = ema
    return result


# ── ATR ───────────────────────────────────────────────────────────────────────

def calculate_atr(ohlcv: List[dict], period: int = 14) -> List[float]:
    """Wilder's ATR. Essential for position sizing and NR7/NR4 context."""
    n = len(ohlcv)
    result = [float("nan")] * n
    if n < period + 1:
        return result
    tr_list = [float("nan")]
    for i in range(1, n):
        hi, lo, pc = ohlcv[i]["high"], ohlcv[i]["low"], ohlcv[i-1]["close"]
        tr_list.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    atr = sum(tr_list[1:period+1]) / period
    result[period] = atr
    for i in range(period + 1, n):
        atr = (atr * (period - 1) + tr_list[i]) / period
        result[i] = atr
    return result


def calculate_atr_pct(ohlcv: List[dict], period: int = 14) -> float:
    atr = calculate_atr(ohlcv, period)
    v = atr[-1]; price = ohlcv[-1]["close"]
    return 0.0 if math.isnan(v) or price == 0 else (v / price) * 100


# ── RSI (Wilder) ──────────────────────────────────────────────────────────────

def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    n = len(closes)
    result = [float("nan")] * n
    if n < period + 1:
        return result
    changes = [closes[i] - closes[i-1] for i in range(1, n)]
    avg_gain = sum(c for c in changes[:period] if c > 0) / period
    avg_loss = sum(abs(c) for c in changes[:period] if c < 0) / period
    result[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, n):
        c = changes[i - 1]
        avg_gain = (avg_gain * (period - 1) + (c  if c > 0 else 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + (-c if c < 0 else 0.0)) / period
        result[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1 + avg_gain / avg_loss)
    return result


# ── DMA Status ────────────────────────────────────────────────────────────────

def calculate_dma_status(closes: List[float]) -> dict:
    """Bug fixed: sma_series no longer returned (was wasting memory on every stock)."""
    s20, s50, s200 = calculate_sma(closes,20), calculate_sma(closes,50), calculate_sma(closes,200)
    last = closes[-1]
    d20, d50, d200 = s20[-1], s50[-1], s200[-1]
    return {
        "above20":  last > d20  if not math.isnan(d20)  else False,
        "above50":  last > d50  if not math.isnan(d50)  else False,
        "above200": not math.isnan(d200) and last > d200,
        "dma20":  0.0 if math.isnan(d20)  else d20,
        "dma50":  0.0 if math.isnan(d50)  else d50,
        "dma200": 0.0 if math.isnan(d200) else d200,
    }


# ── Pattern Detection ─────────────────────────────────────────────────────────

def detect_nr7(data):
    result = [False]*len(data)
    for i in range(6, len(data)):
        ranges = [data[j]["high"]-data[j]["low"] for j in range(i-6,i+1)]
        result[i] = all(r > ranges[-1] for r in ranges[:-1])
    return result

def detect_nr4(data):
    result = [False]*len(data)
    for i in range(3, len(data)):
        ranges = [data[j]["high"]-data[j]["low"] for j in range(i-3,i+1)]
        result[i] = all(r > ranges[-1] for r in ranges[:-1])
    return result

def detect_vcp(data, min_contractions=3):
    """Bug fixed: bar i now included in week-0 (e = i+1 for w=0)."""
    result = [False]*len(data)
    for i in range(30, len(data)):
        weekly = []
        for w in range(4):
            s = i - (w+1)*5
            e = (i+1) if w == 0 else (i - w*5)
            if s < 0: break
            e = min(e, len(data))
            hi = max(d["high"] for d in data[s:e])
            lo = min(d["low"]  for d in data[s:e])
            weekly.append(hi - lo)
        contractions = sum(1 for r in range(1, len(weekly)) if weekly[r] > weekly[r-1])
        result[i] = contractions >= min_contractions - 1
    return result

def detect_pocket_pivot(data, lookback=10):
    result = [False]*len(data)
    for i in range(lookback, len(data)):
        if data[i]["close"] <= data[i-1]["close"]: continue
        max_down = max((data[j]["volume"] for j in range(i-lookback,i)
                        if j>0 and data[j]["close"]<data[j-1]["close"]),default=0)
        result[i] = data[i]["volume"] > max_down > 0
    return result

def detect_rs_divergence(stock, bench, lookback=20):
    result = [False]*len(stock)
    n = min(len(stock), len(bench))
    rs = [stock[i]["close"]/bench[i]["close"] if bench[i]["close"]>0 else 1.0 for i in range(n)]
    for i in range(lookback, n):
        ph = max(d["high"] for d in stock[i-lookback:i])
        price_at_high = stock[i]["close"] >= ph * 0.98
        rs_at_high = rs[i] >= max(rs[i-lookback:i]) * 0.98
        result[i] = not price_at_high and rs_at_high
    return result


# ── Minervini ─────────────────────────────────────────────────────────────────

def validate_minervini_template(ohlcv: List[dict]) -> dict:
    """
    Bug fixed: threshold was 210 → always False on 6mo (~126 bar) data.
    Lowered to 100. Pass 1y data for full SMA200 accuracy.
    """
    if len(ohlcv) < 100:
        return {"passes":False,"reason":"Insufficient history","criteria":{},"criteria_met":0}
    closes = [d["close"] for d in ohlcv]; price = closes[-1]
    sma50  = calculate_sma(closes, min(50,  len(closes)-1))
    sma150 = calculate_sma(closes, min(150, len(closes)-1))
    sma200 = calculate_sma(closes, min(200, len(closes)-1))
    s50,s150,s200 = sma50[-1],sma150[-1],sma200[-1]
    s200_20ago = sma200[-21] if len(sma200)>21 and not math.isnan(sma200[-21]) else s200
    sma200_up  = not math.isnan(s200) and s200 > s200_20ago
    window = ohlcv[-min(252,len(ohlcv)):]
    high52 = max(d["high"] for d in window); low52 = min(d["low"] for d in window)
    pct_hi = (price-high52)/high52*100 if high52>0 else 0.0
    pct_lo = (price-low52)/low52*100   if low52>0  else 0.0
    def ok(v): return not math.isnan(v)
    c = {
        "price_above_150_200": ok(s150) and ok(s200) and price>s150>s200,
        "sma150_above_200":    ok(s150) and ok(s200) and s150>s200,
        "sma200_trending_up":  sma200_up,
        "sma50_above_150_200": ok(s50) and ok(s150) and ok(s200) and s50>s150 and s50>s200 and price>s50,
        "near_52w_high":       pct_hi >= -25,
        "above_52w_low":       pct_lo >= 30,
    }
    passes = all(c.values())
    return {"passes":passes,"criteria":c,"criteria_met":sum(c.values()),
            "pct_from_52w_high":pct_hi,"pct_from_52w_low":pct_lo,
            "sma50":s50,"sma150":s150,"sma200":s200,
            "reason":"All criteria met" if passes else f"Failed: {', '.join(k for k,v in c.items() if not v)}"}


# ── RS Rank ───────────────────────────────────────────────────────────────────

def calculate_rs_rank(rs_scores: List[float]) -> List[int]:
    n = len(rs_scores)
    if n == 0: return []
    if n == 1: return [50]
    indexed = sorted(enumerate(rs_scores), key=lambda x: x[1] if not math.isnan(x[1]) else -999)
    ranks = [50]*n
    for pos,(idx,_) in enumerate(indexed):
        ranks[idx] = max(1, min(99, int((pos/(n-1))*98)+1))
    return ranks


# ── Volume Profile ────────────────────────────────────────────────────────────

def calculate_volume_profile(ohlcv: List[dict], bins: int = 22) -> dict:
    """Bug fixed: bin boundary overlap now uses bin edges (lo+bi*step) not centres ±step/2."""
    if not ohlcv:
        return {"poc":0.0,"vah":0.0,"val":0.0,"bins":[],"max_volume":0.0}
    lo = min(d["low"] for d in ohlcv); hi = max(d["high"] for d in ohlcv)
    if hi <= lo:
        return {"poc":lo,"vah":hi,"val":lo,"bins":[],"max_volume":0.0}
    step = (hi - lo) / bins
    vols = [0.0]*bins
    for bar in ohlcv:
        blo,bhi,vol = bar["low"],bar["high"],bar["volume"]
        br = max(bhi-blo, step*0.01)
        for bi in range(bins):
            bin_lo = lo + bi*step; bin_hi = bin_lo + step
            overlap = max(0.0, min(bin_hi,bhi) - max(bin_lo,blo))
            vols[bi] += vol * overlap / br
    max_v  = max(vols) if vols else 1.0
    poc_i  = vols.index(max_v)
    poc    = lo + (poc_i+0.5)*step
    total  = sum(vols); target = total*0.70
    lo_i,hi_i,accum = poc_i,poc_i,vols[poc_i]
    while accum < target and (lo_i>0 or hi_i<bins-1):
        al = vols[lo_i-1] if lo_i>0 else 0
        ah = vols[hi_i+1] if hi_i<bins-1 else 0
        if ah >= al and hi_i<bins-1: hi_i+=1; accum+=ah
        elif lo_i>0:                 lo_i-=1; accum+=al
        else: break
    buckets = [{"price":lo+(i+0.5)*step,"volume":v} for i,v in enumerate(vols)]
    return {"poc":poc,"vah":lo+(hi_i+1)*step,"val":lo+lo_i*step,"bins":buckets,"max_volume":max_v}


# ── Sector Correlation ────────────────────────────────────────────────────────

def calculate_correlation_matrix(sector_returns: Dict[str,List[float]], window:int=30) -> Dict:
    names = list(sector_returns.keys()); result = {}
    for i,n1 in enumerate(names):
        for n2 in names[i:]:
            r1 = sector_returns[n1][-window:]; r2 = sector_returns[n2][-window:]
            n  = min(len(r1),len(r2))
            if n < 5: result[(n1,n2)] = result[(n2,n1)] = 0.0; continue
            r1,r2 = r1[-n:],r2[-n:]
            m1,m2 = sum(r1)/n, sum(r2)/n
            cov = sum((a-m1)*(b-m2) for a,b in zip(r1,r2))/n
            # Bug fixed: guarded sqrt against floating-point negative values
            s1  = math.sqrt(max(0.0, sum((a-m1)**2 for a in r1)/n))
            s2  = math.sqrt(max(0.0, sum((b-m2)**2 for b in r2)/n))
            corr = cov/(s1*s2) if s1*s2>0 else 0.0
            result[(n1,n2)] = result[(n2,n1)] = round(max(-1.0,min(1.0,corr)),3)
    return result


# ── Breadth ───────────────────────────────────────────────────────────────────

def calculate_advance_decline(stocks_data: List[dict]) -> dict:
    """Bug fixed: None guard on change_pct."""
    advances = sum(1 for s in stocks_data if (s.get("change_pct") or 0) > 0)
    declines = sum(1 for s in stocks_data if (s.get("change_pct") or 0) < 0)
    unchanged = len(stocks_data) - advances - declines
    net = advances - declines
    ratio = net / max(1, advances+declines)
    return {"advances":advances,"declines":declines,"unchanged":unchanged,
            "net":net,"ratio":ratio,
            "breadth_pct":advances/max(1,len(stocks_data))*100,
            "mclellan_approx":ratio*1000}

def count_new_highs_lows(stocks_data: List[dict]) -> dict:
    nh = sum(1 for s in stocks_data if s.get("high52w",0)>0
             and abs(s.get("price",0)-s["high52w"])/s["high52w"]<0.02)
    nl = sum(1 for s in stocks_data if s.get("low52w",0)>0 and s.get("price",0)>0
             and abs(s["price"]-s["low52w"])/s["low52w"]<0.02)
    return {"new_highs":nh,"new_lows":nl,"hl_ratio":nh/max(1,nl)}

def calculate_pct_above_ma(stocks_data: List[dict]) -> dict:
    n = max(1,len(stocks_data))
    return {"above_20dma":sum(1 for s in stocks_data if s.get("above20dma"))/n*100,
            "above_50dma":sum(1 for s in stocks_data if s.get("above50dma"))/n*100,
            "above_200dma":sum(1 for s in stocks_data if s.get("above200dma"))/n*100}

def check_price_continuity(ohlcv: List[dict], threshold: float=0.40) -> List[int]:
    flagged = []
    for i in range(1,len(ohlcv)):
        prev,curr = ohlcv[i-1]["close"],ohlcv[i]["close"]
        if prev>0 and abs(curr-prev)/prev>threshold:
            flagged.append(i)
    return flagged


# ── Momentum Score ────────────────────────────────────────────────────────────

def calculate_momentum_score(data: List[dict]) -> float:
    closes  = [d["close"]  for d in data]
    volumes = [d["volume"] for d in data]
    score   = 0.0
    rsi_arr = calculate_rsi(closes); lr = rsi_arr[-1]
    if not math.isnan(lr):
        score += 25 if 50<=lr<=70 else 15 if lr>70 else 10 if lr>=40 else 0
    dma = calculate_dma_status(closes)
    if dma["above20"]:  score += 10
    if dma["above50"]:  score += 10
    if dma["above200"]: score += 5
    if len(closes)>=20:
        chg = (closes[-1]-closes[-20])/closes[-20]
        score += 25 if chg>0.10 else 20 if chg>0.05 else 10 if chg>0 else 0
    if len(volumes)>=20:
        avg = sum(volumes[-20:])/20; rec = sum(volumes[-5:])/5
        score += 25 if rec>avg*1.5 else 15 if rec>avg else 5
    return min(100.0, score)


# ── Relative Strength ─────────────────────────────────────────────────────────

def calculate_relative_strength(stock, bench, period=50):
    if len(stock)<period or len(bench)<period: return 0.0
    sr = (stock[-1]-stock[-period])/stock[-period] if stock[-period] else 0
    br = (bench[-1]-bench[-period])/bench[-period] if bench[-period] else 0
    return ((1+sr)/(1+br)-1)*100 if (1+br)!=0 else 0


# ── RRG ───────────────────────────────────────────────────────────────────────

def calculate_rrg_values(stock, bench, period=10):
    """
    Bug fixed: NaN RS-Ratio values were filled with 0 before SMA, pulling SMA
    down and producing wrong RS-Momentum. Now forward-fills from last valid value.
    """
    if len(stock)<period*3 or len(bench)<period*3:
        return {"rs_ratio":100.0,"rs_momentum":100.0}
    n = min(len(stock),len(bench))
    rs = [stock[i]/bench[i] if bench[i]>0 else 1.0 for i in range(n)]
    rs_ma = calculate_sma(rs, period)
    rr = [rs[i]/rs_ma[i]*100 if not math.isnan(rs_ma[i]) and rs_ma[i]!=0 else float("nan") for i in range(n)]
    # Forward-fill instead of zero-fill
    filled = []; last = 100.0
    for v in rr:
        if not math.isnan(v): last = v
        filled.append(last)
    rr_ma = calculate_sma(filled, period)
    last_rr,last_rr_ma = rr[-1],rr_ma[-1]
    rs_ratio = 100.0 if math.isnan(last_rr) else last_rr
    rs_mom   = 100.0 if math.isnan(last_rr_ma) or last_rr_ma==0 or math.isnan(last_rr) \
               else last_rr/last_rr_ma*100
    return {"rs_ratio":max(85.0,min(115.0,rs_ratio)),"rs_momentum":max(85.0,min(115.0,rs_mom))}

def get_rrg_quadrant(rs_ratio, rs_momentum):
    if rs_ratio>=100 and rs_momentum>=100: return "Leading"
    if rs_ratio>=100 and rs_momentum<100:  return "Weakening"
    if rs_ratio<100  and rs_momentum<100:  return "Lagging"
    return "Improving"

def calculate_volume_ratio(volumes):
    if len(volumes)<20: return 1.0
    avg = sum(volumes[-20:])/20
    return volumes[-1]/avg if avg>0 else 1.0

def assign_grade(sector_strength, momentum, rs_rank):
    if sector_strength>60 and momentum>70 and rs_rank>70:
        return {"grade":"A","description":"Strong sector + high momentum + top RS rank"}
    if sector_strength>50 and momentum>40:
        return {"grade":"B","description":"Strong sector, moderate strength"}
    return {"grade":"C","description":"Weak sector or low momentum"}
