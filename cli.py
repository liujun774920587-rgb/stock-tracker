"""
cli.py — Command-line interface for the stock tracker.
Use this to fetch prices, generate reports, and manage the watchlist
without opening the Streamlit dashboard.

Usage:
    python cli.py fetch              # Fetch today's prices
    python cli.py report             # Generate and print weekly report
    python cli.py add AAPL MSFT      # Add tickers to watchlist
    python cli.py remove TSLA        # Remove ticker
    python cli.py list               # Show watchlist
    python cli.py history AAPL 30    # Print last 30 days for AAPL
    python cli.py export             # Export weekly report to HTML + CSV
    python cli.py seed               # Load example watchlist and seed 30d of history
"""

import sys
import argparse
import logging

# Configure logging before importing our modules
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

from utils.data_fetcher import StockDataFetcher
from utils.database import StockDatabase
from utils.report_generator import ReportGenerator
from utils.alerts import AlertManager

db = StockDatabase()
fetcher = StockDataFetcher()
reporter = ReportGenerator(db)
alerts = AlertManager(db)


def cmd_fetch(args):
    """Fetch today's prices for all watchlist stocks."""
    tickers = db.get_watchlist()
    if not tickers:
        print("Watchlist is empty. Use: python cli.py add AAPL MSFT")
        return
    print(f"Fetching prices for {len(tickers)} stocks: {', '.join(tickers)}")
    results = fetcher.fetch_all(tickers)
    ok, fail = 0, 0
    for ticker, data in results.items():
        if data:
            db.save_daily_data(ticker, data)
            change = data.get("daily_change_pct", 0)
            sign = "▲" if change >= 0 else "▼"
            print(f"  {ticker:<8} ${data['current_price']:>10,.2f}   {sign} {abs(change):.2f}%")
            ok += 1
        else:
            print(f"  {ticker:<8} — fetch failed")
            fail += 1
    print(f"\nDone. Saved: {ok}  Failed: {fail}")


def cmd_report(args):
    """Generate and print the weekly report."""
    tickers = db.get_watchlist()
    report = reporter.generate_weekly_report(tickers)
    reporter.print_report(report)


def cmd_add(args):
    """Add one or more tickers to the watchlist."""
    for ticker in args.tickers:
        t = ticker.upper()
        info = fetcher.get_stock_info(t)
        if info:
            db.add_to_watchlist(t, info.get("company_name", t))
            print(f"Added: {t} ({info.get('company_name', t)})")
        else:
            print(f"Skipped: {t} — not found on Yahoo Finance")


def cmd_remove(args):
    for ticker in args.tickers:
        db.remove_from_watchlist(ticker.upper())
        print(f"Removed: {ticker.upper()}")


def cmd_list(args):
    tickers = db.get_watchlist()
    if not tickers:
        print("Watchlist is empty.")
    else:
        print("Current watchlist:")
        for t in tickers:
            print(f"  {t}")


def cmd_history(args):
    ticker = args.ticker.upper()
    days = int(args.days) if hasattr(args, "days") and args.days else 30
    hist = db.get_price_history(ticker, days)
    if not hist:
        print(f"No data for {ticker}. Run: python cli.py fetch")
        return
    print(f"\n{ticker} — last {len(hist)} days")
    print(f"{'Date':<12} {'Close':>10} {'Open':>10} {'High':>10} {'Low':>10} {'Change':>8} {'Volume':>12}")
    print("─" * 75)
    for row in hist:
        chg = row.get("daily_change_pct", 0)
        sign = "+" if chg >= 0 else ""
        print(f"{row['date']:<12} ${row['current_price']:>9,.2f} ${row['open_price']:>9,.2f} "
              f"${row['day_high']:>9,.2f} ${row['day_low']:>9,.2f} "
              f"{sign}{chg:>7.2f}% {row['volume']:>12,}")


def cmd_export(args):
    tickers = db.get_watchlist()
    report = reporter.generate_weekly_report(tickers)
    if not report:
        print("No data to export. Run: python cli.py fetch")
        return
    html = reporter.export_html(report)
    csv_path = reporter.export_csv(report)
    print(f"HTML report: {html}")
    print(f"CSV  report: {csv_path}")


def cmd_seed(args):
    """Load the example watchlist and backfill 30 days of historical data."""
    example = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "JPM"]
    print("Loading example watchlist...")
    for t in example:
        db.add_to_watchlist(t, t)
        print(f"  Added {t}")

    print("\nBackfilling 30 days of history (this may take a moment)...")
    for ticker in example:
        records = fetcher.fetch_history(ticker, period="1mo")
        for rec in records:
            db.save_daily_data(ticker, rec)
        print(f"  {ticker}: {len(records)} days saved")

    print("\nDone! Run 'python cli.py report' to see your first report.")


def main():
    parser = argparse.ArgumentParser(description="Stock Tracker CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("fetch", help="Fetch today's prices")
    sub.add_parser("report", help="Print weekly report")

    p_add = sub.add_parser("add", help="Add tickers")
    p_add.add_argument("tickers", nargs="+")

    p_rm = sub.add_parser("remove", help="Remove tickers")
    p_rm.add_argument("tickers", nargs="+")

    sub.add_parser("list", help="Show watchlist")

    p_hist = sub.add_parser("history", help="Show price history")
    p_hist.add_argument("ticker")
    p_hist.add_argument("days", nargs="?", default=30)

    sub.add_parser("export", help="Export weekly report")
    sub.add_parser("seed", help="Load example data")

    args = parser.parse_args()

    commands = {
        "fetch": cmd_fetch,
        "report": cmd_report,
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "history": cmd_history,
        "export": cmd_export,
        "seed": cmd_seed,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
