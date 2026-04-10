import os
import yfinance as yf
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_watchlist():
    res = client.table("watchlist").select("ticker").execute()
    return [r["ticker"] for r in res.data]

def fetch_and_save(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        prev_close = info.get("previousClose") or 0
        daily_change = price - prev_close
        daily_change_pct = (daily_change / prev_close * 100) if prev_close else 0
        client.table("daily_prices").upsert({
            "ticker": ticker,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "company_name": info.get("longName") or ticker,
            "current_price": round(price, 4),
            "open_price": round(info.get("regularMarketOpen") or price, 4),
            "day_high": round(info.get("dayHigh") or price, 4),
            "day_low": round(info.get("dayLow") or price, 4),
            "prev_close": round(prev_close, 4),
            "volume": int(info.get("volume") or 0),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "daily_change": round(daily_change, 4),
            "daily_change_pct": round(daily_change_pct, 4),
            "sector": info.get("sector", "Unknown"),
            "timestamp": datetime.now().isoformat(),
        }).execute()
        print(f"OK {ticker}: ${price:.2f} ({daily_change_pct:+.2f}%)")
    except Exception as e:
        print(f"FAIL {ticker}: {e}")

if __name__ == "__main__":
    tickers = get_watchlist()
    print(f"获取 {len(tickers)} 只股票数据...")
    for ticker in tickers:
        fetch_and_save(ticker)
    print("完成!")
