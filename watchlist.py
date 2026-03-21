"""
Watchlist & Persistence — SQLite
Tables: watchlist, rrg_trail, alerts, breadth_history

Fixes vs previous:
  - Removed unused imports: json, Optional, timedelta
  - datetime.utcnow() → datetime.now(timezone.utc) (Python 3.12 deprecation)
  - evaluate_alerts: vol_ratio None guard (s.get("vol_ratio") or 0)
  - SQLite WAL mode enabled for better concurrent read performance
  - clear_old_alerts throttled via module-level timestamp (not per-render)
"""

import sqlite3
import time
import os
from typing import List
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "pulse_data.db")

# Module-level throttle for clear_old_alerts so it doesn't run on every render
_last_alert_clear: float = 0.0
_ALERT_CLEAR_INTERVAL = 3600.0  # once per hour


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # better concurrent reads
    conn.execute("PRAGMA synchronous=NORMAL") # safe but faster than FULL
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol      TEXT PRIMARY KEY,
            name        TEXT,
            sector      TEXT,
            added_at    REAL DEFAULT (unixepoch()),
            notes       TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS rrg_trail (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sector      TEXT NOT NULL,
            rs_ratio    REAL NOT NULL,
            rs_momentum REAL NOT NULL,
            recorded_at REAL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            alert_type  TEXT NOT NULL,
            message     TEXT NOT NULL,
            price       REAL,
            fired_at    REAL DEFAULT (unixepoch()),
            seen        INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS breadth_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL UNIQUE,
            advances    INTEGER,
            declines    INTEGER,
            new_highs   INTEGER,
            new_lows    INTEGER,
            pct_above20 REAL,
            pct_above50 REAL,
            recorded_at REAL DEFAULT (unixepoch())
        );
        CREATE INDEX IF NOT EXISTS idx_rrg_sector  ON rrg_trail(sector, recorded_at);
        CREATE INDEX IF NOT EXISTS idx_alerts_seen ON alerts(seen, fired_at);
    """)
    conn.commit()
    conn.close()


# ── Watchlist CRUD ────────────────────────────────────────────────────────────

def add_to_watchlist(symbol: str, name: str = "", sector: str = "", notes: str = ""):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO watchlist (symbol, name, sector, notes) VALUES (?,?,?,?)",
        (symbol, name, sector, notes))
    conn.commit(); conn.close()


def remove_from_watchlist(symbol: str):
    conn = _get_conn()
    conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    conn.commit(); conn.close()


def get_watchlist() -> List[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT symbol, name, sector, notes, added_at FROM watchlist ORDER BY added_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_in_watchlist(symbol: str) -> bool:
    conn = _get_conn()
    row  = conn.execute("SELECT 1 FROM watchlist WHERE symbol = ?", (symbol,)).fetchone()
    conn.close()
    return row is not None


def get_watchlist_symbols() -> List[str]:
    conn = _get_conn()
    rows = conn.execute("SELECT symbol FROM watchlist").fetchall()
    conn.close()
    return [r["symbol"] for r in rows]


def get_watchlist_symbols_set() -> set:
    """Batch check — returns a set for O(1) membership tests."""
    conn = _get_conn()
    rows = conn.execute("SELECT symbol FROM watchlist").fetchall()
    conn.close()
    return {r["symbol"] for r in rows}


# ── RRG Trails ────────────────────────────────────────────────────────────────

def record_rrg_snapshot(sector: str, rs_ratio: float, rs_momentum: float):
    """Record once per ~50 min to avoid duplicates on rapid refreshes."""
    conn  = _get_conn()
    last  = conn.execute(
        "SELECT recorded_at FROM rrg_trail WHERE sector=? ORDER BY recorded_at DESC LIMIT 1",
        (sector,)).fetchone()
    if last and (time.time() - last["recorded_at"]) < 3000:
        conn.close(); return
    conn.execute(
        "INSERT INTO rrg_trail (sector, rs_ratio, rs_momentum) VALUES (?,?,?)",
        (sector, rs_ratio, rs_momentum))
    conn.commit(); conn.close()


def get_all_rrg_trails(max_points: int = 12) -> dict:
    """Returns {sector_name: [trail_points oldest-first]}."""
    conn    = _get_conn()
    sectors = conn.execute("SELECT DISTINCT sector FROM rrg_trail").fetchall()
    result  = {}
    for row in sectors:
        s   = row["sector"]
        pts = conn.execute(
            "SELECT rs_ratio, rs_momentum, recorded_at FROM rrg_trail "
            "WHERE sector=? ORDER BY recorded_at DESC LIMIT ?",
            (s, max_points)).fetchall()
        result[s] = [dict(p) for p in reversed(pts)]
    conn.close()
    return result


# ── Alert System ──────────────────────────────────────────────────────────────

def fire_alert(symbol: str, alert_type: str, message: str, price: float = 0.0):
    """Deduplicates: won't re-fire the same alert type for same symbol within 1 hour."""
    conn   = _get_conn()
    recent = conn.execute(
        "SELECT id FROM alerts WHERE symbol=? AND alert_type=? AND fired_at>? LIMIT 1",
        (symbol, alert_type, time.time() - 3600)).fetchone()
    if not recent:
        conn.execute(
            "INSERT INTO alerts (symbol, alert_type, message, price) VALUES (?,?,?,?)",
            (symbol, alert_type, message, float(price or 0)))
        conn.commit()
    conn.close()


def get_unseen_alerts(limit: int = 50) -> List[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, symbol, alert_type, message, price, fired_at FROM alerts "
        "WHERE seen=0 ORDER BY fired_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_alerts(limit: int = 100) -> List[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, symbol, alert_type, message, price, fired_at, seen FROM alerts "
        "ORDER BY fired_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alerts_seen():
    conn = _get_conn()
    conn.execute("UPDATE alerts SET seen=1 WHERE seen=0")
    conn.commit(); conn.close()


def clear_old_alerts(days: int = 7):
    """
    Bug fixed: was running on every page render (expensive SQLite write).
    Now throttled to at most once per hour via module-level timestamp.
    """
    global _last_alert_clear
    if time.time() - _last_alert_clear < _ALERT_CLEAR_INTERVAL:
        return
    _last_alert_clear = time.time()
    conn = _get_conn()
    conn.execute("DELETE FROM alerts WHERE fired_at < ?", (time.time() - days * 86400,))
    conn.commit(); conn.close()


def unseen_alert_count() -> int:
    conn = _get_conn()
    n    = conn.execute("SELECT COUNT(*) FROM alerts WHERE seen=0").fetchone()[0]
    conn.close()
    return n


# ── Alert Evaluation ──────────────────────────────────────────────────────────

def evaluate_alerts(stocks: List[dict]):
    """Fires alerts for all detected signals. Called once per refresh cycle."""
    for s in stocks:
        sym   = s.get("symbol", "")
        price = float(s.get("price") or 0)
        name  = s.get("name", sym)
        volr  = s.get("vol_ratio") or 0   # Bug fixed: was using s['vol_ratio'] directly

        if s.get("is_nr7") and s.get("above50dma") and volr > 1.5:
            fire_alert(sym, "NR7_SETUP",
                f"{name}: NR7 + above 50DMA + vol {volr:.1f}× avg", price)

        if s.get("is_nr4") and s.get("above20dma"):
            fire_alert(sym, "NR4_SETUP",
                f"{name}: NR4 coiling above 20DMA @ ₹{price:.0f}", price)

        if s.get("is_pocket_pivot") and s.get("above50dma"):
            fire_alert(sym, "POCKET_PIVOT",
                f"{name}: Pocket Pivot above 50DMA @ ₹{price:.0f}", price)

        if s.get("is_vcp") and s.get("above50dma"):
            fire_alert(sym, "VCP",
                f"{name}: VCP pattern forming @ ₹{price:.0f}", price)

        if s.get("is_rs_div"):
            fire_alert(sym, "RS_DIVERGENCE",
                f"{name}: RS line leading price — bullish divergence", price)

        if (s.get("rs_rank") or 0) >= 85:
            fire_alert(sym, "TOP_RS",
                f"{name}: RS Rank {s['rs_rank']} — top decile momentum", price)

        if volr > 3.0:
            fire_alert(sym, "VOL_SURGE",
                f"{name}: Volume {volr:.1f}× above average", price)

        if s.get("minervini_passes"):
            fire_alert(sym, "MINERVINI",
                f"{name}: All Minervini SEPA criteria met @ ₹{price:.0f}", price)


# ── Breadth History ───────────────────────────────────────────────────────────

def record_breadth(advances: int, declines: int, new_highs: int, new_lows: int,
                   pct_above20: float, pct_above50: float):
    """Upsert one row per calendar day (IST)."""
    # Bug fixed: datetime.utcnow() deprecated in 3.12 → timezone-aware
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _get_conn()
    conn.execute(
        """INSERT INTO breadth_history
             (date,advances,declines,new_highs,new_lows,pct_above20,pct_above50,recorded_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(date) DO UPDATE SET
             advances=excluded.advances, declines=excluded.declines,
             new_highs=excluded.new_highs, new_lows=excluded.new_lows,
             pct_above20=excluded.pct_above20, pct_above50=excluded.pct_above50,
             recorded_at=excluded.recorded_at""",
        (date_str, advances, declines, new_highs, new_lows,
         pct_above20, pct_above50, time.time()))
    conn.commit(); conn.close()


def get_breadth_history(days: int = 60) -> List[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT date,advances,declines,new_highs,new_lows,pct_above20,pct_above50 "
        "FROM breadth_history ORDER BY date DESC LIMIT ?", (days,)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]  # oldest-first for charts
