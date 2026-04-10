"""
utils/database.py
使用 Supabase 云端数据库存储所有股票数据。
数据永久保存，手机电脑都能访问。
"""

import logging
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# 从 Streamlit secrets 读取配置
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


class StockDatabase:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ── Watchlist ─────────────────────────────────────────────────────────────

    def add_to_watchlist(self, ticker: str, company_name: str = "", sector: str = "Unknown"):
        try:
            self.client.table("watchlist").upsert({
                "ticker": ticker.upper(),
                "company_name": company_name,
                "sector": sector
            }).execute()
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")

    def remove_from_watchlist(self, ticker: str):
        try:
            self.client.table("watchlist").delete().eq("ticker", ticker.upper()).execute()
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")

    def get_watchlist(self) -> list[str]:
        try:
            res = self.client.table("watchlist").select("ticker").order("ticker").execute()
            return [r["ticker"] for r in res.data]
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []

    # ── Daily Prices ──────────────────────────────────────────────────────────

    def save_daily_data(self, ticker: str, data: dict):
        if not data:
            return
        try:
            self.client.table("daily_prices").upsert({
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
            }).execute()
        except Exception as e:
            logger.error(f"Error saving daily data: {e}")

    def get_latest_prices(self, tickers: list[str]) -> list[dict]:
        if not tickers:
            return []
        results = []
        try:
            for ticker in tickers:
                res = self.client.table("daily_prices").select("*").eq(
                    "ticker", ticker).order("date", desc=True).limit(1).execute()
                if res.data:
                    results.append(res.data[0])
        except Exception as e:
            logger.error(f"Error getting latest prices: {e}")
        return results

    def get_price_history(self, ticker: str, days: int = 30) -> list[dict]:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            res = self.client.table("daily_prices").select("*").eq(
                "ticker", ticker.upper()).gte("date", since).order("date").execute()
            return res.data
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return []

    def get_weekly_data(self, ticker: str) -> list[dict]:
        return self.get_price_history(ticker, 7)

    # ── Alerts ────────────────────────────────────────────────────────────────

    def add_alert(self, ticker: str, alert_type: str, threshold: float):
        try:
            self.client.table("alerts").insert({
                "ticker": ticker.upper(),
                "alert_type": alert_type,
                "threshold": threshold
            }).execute()
        except Exception as e:
            logger.error(f"Error adding alert: {e}")

    def get_all_alerts(self) -> list[dict]:
        try:
            res = self.client.table("alerts").select("*").order("ticker").execute()
            return res.data
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    def delete_alert(self, alert_id: int):
        try:
            self.client.table("alerts").delete().eq("id", alert_id).execute()
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")

    def mark_alert_triggered(self, alert_id: int):
        try:
            self.client.table("alerts").update({
                "last_triggered": datetime.now().isoformat()
            }).eq("id", alert_id).execute()
        except Exception as e:
            logger.error(f"Error marking alert: {e}")

    # ── Settings ──────────────────────────────────────────────────────────────

    def save_setting(self, key: str, value: str):
        try:
            self.client.table("settings").upsert({
                "key": key, "value": value
            }).execute()
        except Exception as e:
            logger.error(f"Error saving setting: {e}")

    def get_setting(self, key: str, default: str = "") -> str:
        try:
            res = self.client.table("settings").select("value").eq("key", key).execute()
            return res.data[0]["value"] if res.data else default
        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return default

    # ── Maintenance ───────────────────────────────────────────────────────────

    def clear_all_data(self):
        try:
            self.client.table("daily_prices").delete().neq("id", 0).execute()
        except Exception as e:
            logger.error(f"Error clearing data: {e}")

    def get_db_stats(self) -> dict:
        try:
            res = self.client.table("daily_prices").select("ticker, date").execute()
            tickers = set(r["ticker"] for r in res.data)
            dates = [r["date"] for r in res.data]
            return {
                "total_records": len(res.data),
                "tickers": len(tickers),
                "earliest_date": min(dates) if dates else None
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}