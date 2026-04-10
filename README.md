# 📈 Stock Tracker Pro

A complete stock tracking and analysis tool with a Streamlit dashboard,
daily automated price collection, weekly reports, and customizable alerts.

---

## Project Structure

```
stock_tracker/
├── app.py                  ← Streamlit dashboard (main entry point)
├── cli.py                  ← Command-line interface
├── requirements.txt        ← Python dependencies
├── example_watchlist.csv   ← Import-ready sample watchlist
├── data/
│   └── stocks.db           ← SQLite database (auto-created)
├── reports/                ← Generated HTML & CSV reports (auto-created)
├── charts/                 ← Reserved for saved chart images
└── utils/
    ├── data_fetcher.py     ← Yahoo Finance data fetching (yfinance)
    ├── database.py         ← SQLite storage manager
    ├── alerts.py           ← Price/volume alert engine
    ├── report_generator.py ← Weekly report builder + HTML/CSV export
    └── scheduler.py        ← APScheduler background jobs
```

---

## Quick Start

### 1. Install dependencies

```bash
cd stock_tracker
pip install -r requirements.txt
```

### 2. Option A — Web Dashboard (Recommended)

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### 2. Option B — Command Line Only

```bash
# Load the example watchlist and 30 days of history
python cli.py seed

# Fetch today's prices
python cli.py fetch

# Print weekly report in terminal
python cli.py report

# Export weekly report to HTML + CSV
python cli.py export
```

---

## CLI Commands

| Command | Description |
|---|---|
| `python cli.py seed` | Load example watchlist + 30 days history |
| `python cli.py fetch` | Fetch today's prices for all watchlist stocks |
| `python cli.py report` | Print weekly report in terminal |
| `python cli.py export` | Export report to HTML and CSV in reports/ |
| `python cli.py add AAPL MSFT` | Add tickers to watchlist |
| `python cli.py remove TSLA` | Remove a ticker |
| `python cli.py list` | Show current watchlist |
| `python cli.py history AAPL 30` | Show last 30 days for AAPL |

---

## Dashboard Pages

| Page | What it shows |
|---|---|
| 🏠 Dashboard | Live price cards, candlestick chart, performance bar chart |
| 📋 Watchlist | Add/remove tickers, import from CSV |
| 📊 Weekly Report | Rankings table, per-stock breakdown, download buttons |
| 🔔 Alerts | Set and check price/volume alerts |
| ⚙️ Settings | Scheduler times, email, benchmark |

---

## Customizing Your Watchlist

**Via dashboard:** Go to 📋 Watchlist → type tickers → Add

**Via CLI:**
```bash
python cli.py add NVDA AMD INTC
python cli.py remove META
```

**Via CSV import:** Edit `example_watchlist.csv` (one ticker per line),
then use the dashboard's "Import from CSV" button.

---

## Customizing Alerts

Go to 🔔 Alerts in the dashboard and add rules such as:

| Alert type | Example |
|---|---|
| Price Above | AAPL above $220 — notify when it breaks resistance |
| Price Below | TSLA below $150 — stop-loss warning |
| Daily Move > | Any stock moves more than 5% in a day |
| Volume Spike > | Volume 50% above average (enter 50 as threshold) |

---

## Automation (Scheduler)

The scheduler starts automatically when the Streamlit app runs.

Default schedule:
- **Daily:** Weekdays at 4:31 PM Eastern (just after US market close)
- **Weekly:** Fridays at 5:00 PM Eastern

Change the times in ⚙️ Settings, or edit `utils/scheduler.py` directly.

To run the scheduler standalone (no dashboard):
```bash
python -c "
from utils.data_fetcher import StockDataFetcher
from utils.database import StockDatabase
from utils.report_generator import ReportGenerator
from utils.scheduler import SchedulerManager
import time

db = StockDatabase()
fetcher = StockDataFetcher()
reporter = ReportGenerator(db)
sched = SchedulerManager(fetcher, db, reporter)
sched.start()
print('Scheduler running. Press Ctrl+C to stop.')
while True: time.sleep(60)
"
```

---

## Weekly Report Contents

For each stock over the past 7 trading days:
- Weekly open and close prices
- Weekly high and low
- Total percentage return
- Average daily volume
- Trend classification (Strong Uptrend / Mild Uptrend / etc.)

Summary section:
- Best and worst performer
- Average return across watchlist
- Full ranked table

Export formats: HTML (styled), CSV (for Excel/Sheets)

---

## Email Notifications

1. Go to ⚙️ Settings in the dashboard
2. Enter your email address and SMTP credentials
3. Gmail example:
   - SMTP host: `smtp.gmail.com`
   - Port: `587`
   - Username: your Gmail address
   - Password: an App Password (not your regular Gmail password)
     — generate at myaccount.google.com → Security → App passwords

The weekly report will be emailed as an HTML attachment every Friday.

---

## Benchmark Comparison (S&P 500)

1. Go to ⚙️ Settings → Benchmark Comparison
2. Select `^GSPC (S&P 500)`
3. The weekly report will include S&P 500 return for comparison

---

## Sector Grouping

Sector data is fetched automatically via yfinance and stored in the database.
The dashboard's performance comparison chart can be extended to group by sector.

---

## Data Storage

All data is stored in `data/stocks.db` (SQLite).

- Duplicate entries for the same ticker + date are automatically prevented.
- Historical data accumulates automatically with each daily fetch.
- You can inspect the database with any SQLite viewer or:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/stocks.db')
rows = conn.execute('SELECT ticker, date, current_price FROM daily_prices ORDER BY date DESC LIMIT 20').fetchall()
for r in rows: print(r)
"
```

---

## Troubleshooting

**Ticker not found?**
- Make sure it's a valid Yahoo Finance symbol (e.g., `BRK-B` not `BRKB`)
- Some ETFs or foreign stocks may not be available

**No data showing?**
- Click 🔄 Refresh Prices in the sidebar, or run `python cli.py fetch`

**APScheduler warning?**
- Install it: `pip install apscheduler`
- Or just use manual refresh — the app works fully without the scheduler

---

## Data Source

All market data is sourced from **Yahoo Finance** via the `yfinance` library.
This is free and does not require an API key. Data may be delayed 15 minutes
during market hours.
