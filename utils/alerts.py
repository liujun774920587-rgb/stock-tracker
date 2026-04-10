"""
utils/alerts.py
Checks price/volume conditions against stored alert rules.
Triggered alerts are logged and can be sent via email.
"""

import logging
from utils.database import StockDatabase

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alert rules and evaluates them against current market data.
    """

    def __init__(self, db: StockDatabase):
        self.db = db

    def add_alert(self, ticker: str, alert_type: str, threshold: float):
        self.db.add_alert(ticker, alert_type, threshold)

    def get_all_alerts(self) -> list[dict]:
        return self.db.get_all_alerts()

    def delete_alert(self, alert_id: int):
        self.db.delete_alert(alert_id)

    def check_alerts(self, latest_prices: list[dict]) -> list[dict]:
        """
        Evaluate all active alerts against the latest price snapshot.
        Returns a list of triggered alert dicts with a human-readable message.
        """
        alerts = self.db.get_all_alerts()
        price_map = {s["ticker"]: s for s in latest_prices}
        triggered = []

        for alert in alerts:
            if not alert["active"]:
                continue
            ticker = alert["ticker"]
            atype = alert["alert_type"]
            threshold = alert["threshold"]
            data = price_map.get(ticker)
            if not data:
                continue

            price = data.get("current_price", 0)
            change_pct = abs(data.get("daily_change_pct", 0))
            volume = data.get("volume", 0)
            avg_vol = self._avg_volume(ticker)

            message = None
            if atype == "Price Above" and price > threshold:
                message = f"{ticker} price ${price:.2f} is ABOVE target ${threshold:.2f}"
            elif atype == "Price Below" and price < threshold:
                message = f"{ticker} price ${price:.2f} is BELOW target ${threshold:.2f}"
            elif atype == "Daily Move >" and change_pct > threshold:
                message = f"{ticker} moved {change_pct:.2f}% today (threshold: {threshold}%)"
            elif atype == "Volume Spike >" and avg_vol and volume > avg_vol * (threshold / 100 + 1):
                message = f"{ticker} volume {volume:,} is a spike vs avg {avg_vol:,.0f}"

            if message:
                triggered.append({"ticker": ticker, "alert_id": alert["id"], "message": message})
                self.db.mark_alert_triggered(alert["id"])
                logger.info(f"Alert triggered: {message}")

        return triggered

    def _avg_volume(self, ticker: str, days: int = 20) -> float | None:
        """Return average daily volume over last N days from DB."""
        history = self.db.get_price_history(ticker, days)
        volumes = [r["volume"] for r in history if r.get("volume")]
        return sum(volumes) / len(volumes) if volumes else None
