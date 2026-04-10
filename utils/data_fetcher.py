"""
utils/data_fetcher.py
Fetches stock data from Yahoo Finance using yfinance.
Handles errors gracefully and returns clean data dictionaries.
"""

import yfinance as yf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """
    Fetches stock data from Yahoo Finance.
    All methods return None or empty dicts on failure — never crash the app.
    """

    def get_stock_info(self, ticker: str) -> dict | None:
        """
        Validate a ticker and return basic company info.
        Returns None if the ticker is invalid.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            # yfinance returns an empty or minimal dict for invalid tickers
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                # Try fetching 1-day history to confirm existence
                hist = stock.history(period="1d")
                if hist.empty:
                    logger.warning(f"Ticker not found: {ticker}")
                    return None
            return {
                "ticker": ticker.upper(),
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
            }
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return None

    def fetch_daily_data(self, ticker: str) -> dict | None:
        """
        Fetch full daily snapshot for a single ticker.
        Returns a dictionary with all fields needed for storage.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Current price — try multiple fields
            price = (
                info.get("currentPrice") or
                info.get("regularMarketPrice") or
                info.get("previousClose") or
                0.0
            )
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or 0.0
            open_price = info.get("regularMarketOpen") or info.get("open") or price
            day_high = info.get("dayHigh") or info.get("regularMarketDayHigh") or price
            day_low = info.get("dayLow") or info.get("regularMarketDayLow") or price
            volume = info.get("volume") or info.get("regularMarketVolume") or 0

            # Calculate daily change
            daily_change = price - prev_close if prev_close else 0.0
            daily_change_pct = (daily_change / prev_close * 100) if prev_close else 0.0

            return {
                "ticker": ticker.upper(),
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "current_price": round(price, 4),
                "open_price": round(open_price, 4),
                "day_high": round(day_high, 4),
                "day_low": round(day_low, 4),
                "prev_close": round(prev_close, 4),
                "volume": int(volume),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                "week52_high": info.get("fiftyTwoWeekHigh"),
                "week52_low": info.get("fiftyTwoWeekLow"),
                "daily_change": round(daily_change, 4),
                "daily_change_pct": round(daily_change_pct, 4),
                "sector": info.get("sector", "Unknown"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None

    def fetch_all(self, tickers: list[str]) -> dict[str, dict | None]:
        """
        Fetch daily data for all tickers in the watchlist.
        Returns a dict: {ticker: data_dict or None}
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.fetch_daily_data(ticker)
            if results[ticker] is None:
                logger.warning(f"No data returned for {ticker}")
        return results

    def fetch_history(self, ticker: str, period: str = "1mo") -> list[dict]:
        """
        Fetch OHLCV historical data for a ticker.
        period options: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'
        Returns a list of daily records sorted oldest-first.
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty:
                return []

            records = []
            for date, row in hist.iterrows():
                records.append({
                    "ticker": ticker.upper(),
                    "date": date.strftime("%Y-%m-%d"),
                    "open_price": round(float(row["Open"]), 4),
                    "day_high": round(float(row["High"]), 4),
                    "day_low": round(float(row["Low"]), 4),
                    "current_price": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                    "daily_change": 0,
                    "daily_change_pct": 0,
                })
            # Fill in daily change values
            for i in range(1, len(records)):
                prev = records[i - 1]["current_price"]
                curr = records[i]["current_price"]
                if prev:
                    records[i]["daily_change"] = round(curr - prev, 4)
                    records[i]["daily_change_pct"] = round((curr - prev) / prev * 100, 4)

            return records
        except Exception as e:
            logger.error(f"Error fetching history for {ticker}: {e}")
            return []
