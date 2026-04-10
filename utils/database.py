"""
utils/database.py
Manages all SQLite storage: watchlist, daily prices, alerts, settings.
Uses context managers so connections are always closed cleanly.
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database stored in the data/ folder next to this package
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stocks.db")


class StockDatabase:
    """
    All database operations for the stock tracker.
    Tables:
        watchlist       — tickers the user wants to track
        daily_prices    — one row per (ticker, date)
        alerts          — user-defined price/volume alerts
        settings        — key-value app settings
    """

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_tables()

    @contextmanager
    def _conn(self):
        """Yield a connection and always close it when done."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # rows behave like dicts
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """Create tables if they don't exist yet."""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    ticker       TEXT PRIMARY KEY,
                    company_name TEXT,
                    sector       TEXT DEFAULT 'Unknown',
                    added_date   TEXT DEFAULT CURRENT_DATE
                );

                CREATE TABLE IF NOT EXISTS daily_prices (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker           TEXT NOT NULL,
                    date             TEXT NOT NULL,
                    company_name     TEXT,
                    current_price    REAL,
                    open_price       REAL,
                    day_high         REAL,
                    day_low          REAL,
                    prev_close       REAL,
                    volume           INTEGER,
                    market_cap       REAL,
                    pe_ratio         REAL,
                    week52_high      REAL,
                    week52_low       REAL,
                    daily_change     REAL,
                    daily_change_pct REAL,
                    sector           TEXT,
                    timestamp        TEXT,
                    UNIQUE(ticker, date)
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker       TEXT NOT NULL,
                    alert_type   TEXT NOT NULL,
                    threshold    REAL NOT NULL,
                    active       INTEGER DEFAULT 1,
                    created_date TEXT DEFAULT CURRENT_DATE,
                    last_triggered TEXT
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    # ── Watchlist ─────────────────────────────────────────────────────────────

    def add_to_watchlist(self, ticker: str, company_name: str = "", sector: str = "Unknown"):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, company_name, sector) VALUES (?, ?, ?)",
                (ticker.upper(), company_name, sector)
            )

    def remove_from_watchlist(self, ticker: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))

    def get_watchlist(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT ticker FROM watchlist ORDER BY ticker").fetchall()
        return [r["ticker"] for r in rows]

    # ── Daily Prices ──────────────────────────────────────────────────────────

    def save_daily_data(self, ticker: str, data: dict):
        """
        Insert or replace a daily snapshot.
        The UNIQUE(ticker, date) constraint prevents duplicates.
        """
        if not data:
            return
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_prices
                    (ticker, date, company_name, current_price, open_price, day_high, day_low,
                     prev_close, volume, market_cap, pe_ratio, week52_high, week52_low,
                     daily_change, daily_change_pct, sector, timestamp)
                VALUES
                    (:ticker, :date, :company_name, :current_price, :open_price, :day_high, :day_low,
                     :prev_close, :volume, :market_cap, :pe_ratio, :week52_high, :week52_low,
                     :daily_change, :daily_change_pct, :sector, :timestamp)
            """, {
                "ticker": ticker.upper(),
                "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "company_name": data.get("company_name", ticker),
                "current_price": data.get("current_price"),
                "open_price": data.get("open_price"),
                "day_high": data.get("day_high"),
                "day_low": data.get("day_low"),
                "prev_close": data.get("prev_close"),
                "volume": data.get("volume"),
                "market_cap": data.get("market_cap"),
                "pe_ratio": data.get("pe_ratio"),
                "week52_high": data.get("week52_high"),
                "week52_low": data.get("week52_low"),
                "daily_change": data.get("daily_change"),
                "daily_change_pct": data.get("daily_change_pct"),
                "sector": data.get("sector", "Unknown"),
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
            })

    def get_latest_prices(self, tickers: list[str]) -> list[dict]:
        """Return the most recent price record for each ticker."""
        if not tickers:
            return []
        results = []
        with self._conn() as conn:
            for ticker in tickers:
                row = conn.execute(
                    "SELECT * FROM daily_prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                    (ticker,)
                ).fetchone()
                if row:
                    results.append(dict(row))
        return results

    def get_price_history(self, ticker: str, days: int = 30) -> list[dict]:
        """Return daily price rows for a ticker over the last N days."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_prices WHERE ticker = ? AND date >= ? ORDER BY date ASC",
                (ticker.upper(), since)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_weekly_data(self, ticker: str) -> list[dict]:
        """Return daily records for the past 7 calendar days."""
        return self.get_price_history(ticker, 7)

    # ── Alerts ────────────────────────────────────────────────────────────────

    def add_alert(self, ticker: str, alert_type: str, threshold: float):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO alerts (ticker, alert_type, threshold) VALUES (?, ?, ?)",
                (ticker.upper(), alert_type, threshold)
            )

    def get_all_alerts(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM alerts ORDER BY ticker").fetchall()
        return [dict(r) for r in rows]

    def delete_alert(self, alert_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))

    def mark_alert_triggered(self, alert_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE alerts SET last_triggered = ? WHERE id = ?",
                (datetime.now().isoformat(), alert_id)
            )

    # ── Settings ──────────────────────────────────────────────────────────────

    def save_setting(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def get_setting(self, key: str, default: str = "") -> str:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    # ── Maintenance ───────────────────────────────────────────────────────────

    def clear_all_data(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM daily_prices")

    def get_db_stats(self) -> dict:
        with self._conn() as conn:
            n_prices = conn.execute("SELECT COUNT(*) as c FROM daily_prices").fetchone()["c"]
            n_tickers = conn.execute("SELECT COUNT(DISTINCT ticker) as c FROM daily_prices").fetchone()["c"]
            earliest = conn.execute("SELECT MIN(date) as d FROM daily_prices").fetchone()["d"]
        return {"total_records": n_prices, "tickers": n_tickers, "earliest_date": earliest}
