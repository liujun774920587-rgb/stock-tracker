"""
utils/report_generator.py
Builds the weekly summary report from stored daily data.
Can export to HTML and CSV.
"""

import os
import csv
import logging
from datetime import datetime
from utils.database import StockDatabase

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


class ReportGenerator:
    """
    Generates weekly performance reports from 7 days of stored price data.
    """

    def __init__(self, db: StockDatabase):
        self.db = db
        os.makedirs(REPORTS_DIR, exist_ok=True)

    def generate_weekly_report(self, tickers: list[str]) -> dict:
        """
        Build a full weekly report dict for all tickers.
        Structure:
            {
              summary: { best_ticker, worst_ticker, avg_return, ... },
              rankings: [ { ticker, company, weekly_return_pct, ... }, ... ],
              stocks:   { ticker: { week_open, week_close, ... }, ... }
            }
        """
        if not tickers:
            return {}

        stock_data = {}
        for ticker in tickers:
            rows = self.db.get_weekly_data(ticker)
            if not rows:
                continue
            rows_sorted = sorted(rows, key=lambda r: r["date"])
            week_open = rows_sorted[0]["open_price"] or rows_sorted[0]["current_price"]
            week_close = rows_sorted[-1]["current_price"]
            week_high = max(r["day_high"] for r in rows_sorted if r["day_high"])
            week_low = min(r["day_low"] for r in rows_sorted if r["day_low"])
            volumes = [r["volume"] for r in rows_sorted if r["volume"]]
            avg_vol = sum(volumes) / len(volumes) if volumes else 0
            weekly_return = ((week_close - week_open) / week_open * 100) if week_open else 0

            # Trend label
            if weekly_return > 3:
                trend = "📈 Strong Uptrend"
            elif weekly_return > 0:
                trend = "↗ Mild Uptrend"
            elif weekly_return > -3:
                trend = "↘ Mild Downtrend"
            else:
                trend = "📉 Strong Downtrend"

            stock_data[ticker] = {
                "ticker": ticker,
                "company_name": rows_sorted[-1].get("company_name", ticker),
                "week_open": round(week_open, 4),
                "week_close": round(week_close, 4),
                "week_high": round(week_high, 4),
                "week_low": round(week_low, 4),
                "avg_volume": round(avg_vol),
                "weekly_return_pct": round(weekly_return, 2),
                "trend": trend,
                "days_tracked": len(rows_sorted),
            }

        if not stock_data:
            return {}

        # Rankings
        rankings = sorted(stock_data.values(), key=lambda x: x["weekly_return_pct"], reverse=True)
        rank_list = [
            {
                "Rank": i + 1,
                "Ticker": r["ticker"],
                "Company": r["company_name"],
                "Week Open": f"${r['week_open']:,.2f}",
                "Week Close": f"${r['week_close']:,.2f}",
                "Weekly Return %": r["weekly_return_pct"],
                "Trend": r["trend"],
            }
            for i, r in enumerate(rankings)
        ]

        best = rankings[0]
        worst = rankings[-1]
        avg_ret = sum(r["weekly_return_pct"] for r in rankings) / len(rankings)

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "best_ticker": best["ticker"],
                "best_return": best["weekly_return_pct"],
                "worst_ticker": worst["ticker"],
                "worst_return": worst["weekly_return_pct"],
                "avg_return": round(avg_ret, 2),
                "stocks_tracked": len(stock_data),
            },
            "rankings": rank_list,
            "stocks": stock_data,
        }
        return report

    # ── HTML Export ───────────────────────────────────────────────────────────

    def export_html(self, report: dict) -> str | None:
        """Write a styled HTML report and return its file path."""
        if not report:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(REPORTS_DIR, f"weekly_report_{timestamp}.html")
        summary = report.get("summary", {})
        rankings = report.get("rankings", [])

        rows_html = ""
        for r in rankings:
            ret = r["Weekly Return %"]
            color = "#00d4aa" if ret >= 0 else "#ff4757"
            sign = "+" if ret >= 0 else ""
            rows_html += f"""
            <tr>
                <td>{r['Rank']}</td>
                <td><strong>{r['Ticker']}</strong></td>
                <td>{r['Company']}</td>
                <td>{r['Week Open']}</td>
                <td>{r['Week Close']}</td>
                <td style="color:{color};font-weight:700;">{sign}{ret:.2f}%</td>
                <td>{r['Trend']}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Weekly Stock Report — {datetime.now().strftime('%B %d, %Y')}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0e1a; color: #e2e8f0; padding: 40px; }}
  h1 {{ font-size: 2rem; color: #3b82f6; margin-bottom: 4px; }}
  .subtitle {{ color: #64748b; margin-bottom: 40px; }}
  .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }}
  .card {{ background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; }}
  .card-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; }}
  .card-value {{ font-size: 2rem; font-weight: 700; margin-top: 8px; font-family: monospace; }}
  .green {{ color: #00d4aa; }} .red {{ color: #ff4757; }} .blue {{ color: #3b82f6; }}
  table {{ width: 100%; border-collapse: collapse; background: #111827; border-radius: 12px; overflow: hidden; }}
  th {{ background: #1a2235; padding: 14px 16px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }}
  td {{ padding: 14px 16px; border-bottom: 1px solid #1e293b; }}
  tr:last-child td {{ border-bottom: none; }}
  .footer {{ margin-top: 40px; text-align: center; color: #64748b; font-size: 0.85rem; }}
</style>
</head>
<body>
  <h1>📈 Weekly Stock Report</h1>
  <p class="subtitle">Generated {datetime.now().strftime('%A, %B %d, %Y at %H:%M')}</p>

  <div class="cards">
    <div class="card">
      <div class="card-label">Best Performer</div>
      <div class="card-value green">{summary.get('best_ticker','—')}</div>
      <div class="green">+{summary.get('best_return',0):.2f}%</div>
    </div>
    <div class="card">
      <div class="card-label">Worst Performer</div>
      <div class="card-value red">{summary.get('worst_ticker','—')}</div>
      <div class="red">{summary.get('worst_return',0):.2f}%</div>
    </div>
    <div class="card">
      <div class="card-label">Avg Weekly Return</div>
      <div class="card-value {'green' if summary.get('avg_return',0) >= 0 else 'red'}">{summary.get('avg_return',0):+.2f}%</div>
      <div style="color:#64748b">{summary.get('stocks_tracked',0)} stocks tracked</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Rank</th><th>Ticker</th><th>Company</th>
        <th>Week Open</th><th>Week Close</th><th>Weekly Return</th><th>Trend</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>

  <div class="footer">Stock Tracker Pro — Data sourced from Yahoo Finance via yfinance</div>
</body>
</html>"""

        with open(path, "w") as f:
            f.write(html)
        logger.info(f"HTML report saved: {path}")
        return path

    # ── CSV Export ────────────────────────────────────────────────────────────

    def export_csv(self, report: dict) -> str | None:
        if not report:
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(REPORTS_DIR, f"weekly_report_{timestamp}.csv")
        rankings = report.get("rankings", [])
        if not rankings:
            return None
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rankings[0].keys())
            writer.writeheader()
            writer.writerows(rankings)
        logger.info(f"CSV report saved: {path}")
        return path

    # ── Terminal Print ────────────────────────────────────────────────────────

    def print_report(self, report: dict):
        """Print a clean terminal summary of the weekly report."""
        if not report:
            print("No report data available.")
            return
        summary = report.get("summary", {})
        print("\n" + "═" * 65)
        print(f"  📈  WEEKLY STOCK REPORT  —  {datetime.now().strftime('%B %d, %Y')}")
        print("═" * 65)
        print(f"  Best Performer : {summary.get('best_ticker','—'):6s}  ({summary.get('best_return',0):+.2f}%)")
        print(f"  Worst Performer: {summary.get('worst_ticker','—'):6s}  ({summary.get('worst_return',0):+.2f}%)")
        print(f"  Average Return : {summary.get('avg_return',0):+.2f}%")
        print("─" * 65)
        print(f"  {'#':<3} {'Ticker':<8} {'Open':>10} {'Close':>10} {'Return':>9} {'Trend'}")
        print("─" * 65)
        for r in report.get("rankings", []):
            ret = r["Weekly Return %"]
            print(f"  {r['Rank']:<3} {r['Ticker']:<8} {r['Week Open']:>10} {r['Week Close']:>10} {ret:>+8.2f}%  {r['Trend']}")
        print("═" * 65 + "\n")
