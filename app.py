"""
Stock Tracker - Main Streamlit Dashboard
Run with: streamlit run app.py
"""

import streamlit as st
import time
# 每5分钟自动刷新页面
st_autorefresh = st.empty()
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time

# Import our custom modules
from utils.data_fetcher import StockDataFetcher
from utils.database import StockDatabase
from utils.alerts import AlertManager
from utils.report_generator import ReportGenerator
from utils.scheduler import SchedulerManager

# ─── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Tracker Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

    :root {
        --bg-primary: #0a0e1a;
        --bg-card: #111827;
        --bg-card2: #1a2235;
        --accent-green: #00d4aa;
        --accent-red: #ff4757;
        --accent-blue: #3b82f6;
        --accent-yellow: #fbbf24;
        --text-primary: #e2e8f0;
        --text-muted: #64748b;
        --border: #1e293b;
    }

    .stApp { background-color: var(--bg-primary); }

    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: var(--accent-blue); }

    .ticker-symbol {
        font-family: 'Space Mono', monospace;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--accent-blue);
    }

    .price-positive { color: var(--accent-green) !important; }
    .price-negative { color: var(--accent-red) !important; }

    .alert-badge {
        background: var(--accent-yellow);
        color: #000;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .section-header {
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border);
    }

    div[data-testid="stMetricValue"] { font-family: 'Space Mono', monospace; }
    div[data-testid="stSidebar"] { background-color: var(--bg-card) !important; }
</style>
""", unsafe_allow_html=True)

# ─── Initialize Services ──────────────────────────────────────────────────────
@st.cache_resource
def init_services():
    db = StockDatabase()
    fetcher = StockDataFetcher()
    alerts = AlertManager(db)
    reporter = ReportGenerator(db)
    return db, fetcher, alerts, reporter

db, fetcher, alerts, reporter = init_services()


# ─── Session State ────────────────────────────────────────────────────────────
if "watchlist" not in st.session_state:
    st.session_state.watchlist = db.get_watchlist()
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Stock Tracker Pro")
    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📋 Watchlist", "📊 Weekly Report", "🔔 Alerts", "⚙️ Settings"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Quick refresh button
    if st.button("🔄 Refresh Prices", use_container_width=True):
        with st.spinner("Fetching latest prices..."):
            results = fetcher.fetch_all(st.session_state.watchlist)
            for ticker, data in results.items():
                if data:
                    db.save_daily_data(ticker, data)
            st.session_state.last_refresh = datetime.now()
        st.success(f"Updated {len(results)} stocks!")
        st.rerun()

    if st.session_state.last_refresh:
        st.caption(f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

    st.markdown("---")

    # Market status indicator
    now = datetime.now()
    market_open = now.weekday() < 5 and 9 <= now.hour < 16
    status_color = "🟢" if market_open else "🔴"
    st.markdown(f"{status_color} Market {'Open' if market_open else 'Closed'}")
    st.caption(f"Today: {now.strftime('%A, %b %d %Y')}")

# ─── Page: Dashboard ──────────────────────────────────────────────────────────
if page == "🏠 Dashboard":

    watchlist = st.session_state.watchlist
    if not watchlist:
        st.info("👈 Add stocks to your watchlist to get started.")
    else:
        # Fetch latest data
        latest = db.get_latest_prices(watchlist)

        # ── Top Summary Metrics ──
        if latest:
            gainers = [s for s in latest if s.get("daily_change_pct", 0) > 0]
            losers = [s for s in latest if s.get("daily_change_pct", 0) < 0]
            avg_change = sum(s.get("daily_change_pct", 0) for s in latest) / len(latest)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Stocks Tracked", len(watchlist))
            col2.metric("Gainers Today", len(gainers), delta=f"+{len(gainers)}")
            col3.metric("Losers Today", len(losers), delta=f"-{len(losers)}", delta_color="inverse")
            col4.metric("Avg Change", f"{avg_change:+.2f}%",
                       delta="positive" if avg_change > 0 else "negative")

        st.markdown("---")

        # ── Stock Cards Grid ──
        st.markdown('<p class="section-header">Current Watchlist</p>', unsafe_allow_html=True)

        cols_per_row = 3
        for i in range(0, len(watchlist), cols_per_row):
            cols = st.columns(cols_per_row)
            batch = watchlist[i:i + cols_per_row]
            for j, ticker in enumerate(batch):
                data = next((s for s in latest if s["ticker"] == ticker), None)
                with cols[j]:
                    if data:
                        change_pct = data.get("daily_change_pct", 0)
                        change_val = data.get("daily_change", 0)
                        color = "#00d4aa" if change_pct >= 0 else "#ff4757"
                        arrow = "▲" if change_pct >= 0 else "▼"

                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="display:flex; justify-content:space-between; align-items:start;">
                                <span class="ticker-symbol">{ticker}</span>
                                <span style="color:{color}; font-size:0.85rem; font-weight:600;">{arrow} {abs(change_pct):.2f}%</span>
                            </div>
                            <div style="font-size:0.8rem; color:#64748b; margin:2px 0 10px;">{data.get('company_name','')}</div>
                            <div style="font-size:1.8rem; font-weight:700; font-family:'Space Mono',monospace; color:#e2e8f0;">
                                ${data.get('current_price', 0):,.2f}
                            </div>
                            <div style="font-size:0.8rem; color:{color}; margin-top:4px;">{arrow} ${abs(change_val):.2f} today</div>
                            <div style="margin-top:12px; display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:0.75rem; color:#64748b;">
                                <span>H: ${data.get('day_high', 0):,.2f}</span>
                                <span>L: ${data.get('day_low', 0):,.2f}</span>
                                <span>Open: ${data.get('open_price', 0):,.2f}</span>
                                <span>Vol: {data.get('volume', 0)/1e6:.1f}M</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="metric-card">
                            <span class="ticker-symbol">{ticker}</span>
                            <div style="color:#64748b; margin-top:8px; font-size:0.85rem;">No data — click Refresh</div>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Price Charts ──
        st.markdown('<p class="section-header">Price Trends (7-Day)</p>', unsafe_allow_html=True)

        chart_ticker = st.selectbox("Select stock for chart", watchlist)
        chart_period = st.radio("Period", ["7D", "1M", "3M"], horizontal=True)

        period_map = {"7D": 7, "1M": 30, "3M": 90}
        days = period_map[chart_period]
        hist = db.get_price_history(chart_ticker, days)

        if hist:
            df = pd.DataFrame(hist)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            fig = go.Figure()
            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df["date"],
                open=df["open_price"],
                high=df["day_high"],
                low=df["day_low"],
                close=df["current_price"],
                name=chart_ticker,
                increasing_line_color="#00d4aa",
                decreasing_line_color="#ff4757"
            ))
            # Volume bars
            fig.add_trace(go.Bar(
                x=df["date"], y=df["volume"],
                name="Volume", opacity=0.3,
                marker_color="#3b82f6",
                yaxis="y2"
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_rangeslider_visible=False,
                height=400,
                yaxis2=dict(overlaying="y", side="right", showgrid=False),
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(orientation="h", y=1.02)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data yet. Refresh prices to start collecting data.")

        # ── Performance Comparison ──
        st.markdown('<p class="section-header">Performance Comparison</p>', unsafe_allow_html=True)
        perf_data = []
        for ticker in watchlist:
            hist7 = db.get_price_history(ticker, 7)
            if len(hist7) >= 2:
                df_h = pd.DataFrame(hist7).sort_values("date")
                start_p = df_h.iloc[0]["current_price"]
                end_p = df_h.iloc[-1]["current_price"]
                if start_p > 0:
                    perf_data.append({"Ticker": ticker, "7D Return %": round((end_p - start_p) / start_p * 100, 2)})

        if perf_data:
            df_perf = pd.DataFrame(perf_data).sort_values("7D Return %", ascending=True)
            colors = ["#00d4aa" if v >= 0 else "#ff4757" for v in df_perf["7D Return %"]]
            fig2 = go.Figure(go.Bar(
                x=df_perf["7D Return %"], y=df_perf["Ticker"],
                orientation="h", marker_color=colors
            ))
            fig2.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=300,
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig2, use_container_width=True)

# ─── Page: Watchlist Management ───────────────────────────────────────────────
elif page == "📋 Watchlist":
    st.title("📋 Watchlist Manager")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Add Stocks")
        new_tickers = st.text_input(
            "Enter ticker symbols (comma-separated)",
            placeholder="AAPL, MSFT, NVDA, AMZN"
        )
        col_a, col_b = st.columns(2)
        if col_a.button("➕ Add to Watchlist", use_container_width=True):
            if new_tickers:
                tickers = [t.strip().upper() for t in new_tickers.split(",")]
                added, failed = [], []
                for ticker in tickers:
                    info = fetcher.get_stock_info(ticker)
                    if info:
                        db.add_to_watchlist(ticker, info.get("company_name", ticker))
                        added.append(ticker)
                    else:
                        failed.append(ticker)
                st.session_state.watchlist = db.get_watchlist()
                if added:
                    st.success(f"Added: {', '.join(added)}")
                if failed:
                    st.error(f"Not found: {', '.join(failed)}")

        # CSV Import
        uploaded = st.file_uploader("Or import from CSV (one ticker per row)", type="csv")
        if uploaded:
            import_df = pd.read_csv(uploaded, header=None)
            import_tickers = import_df.iloc[:, 0].str.upper().tolist()
            if st.button(f"Import {len(import_tickers)} tickers"):
                for t in import_tickers:
                    db.add_to_watchlist(t, t)
                st.session_state.watchlist = db.get_watchlist()
                st.success(f"Imported {len(import_tickers)} tickers!")

    with col2:
        st.subheader("Current Watchlist")
        wl = st.session_state.watchlist
        if wl:
            for ticker in wl:
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{ticker}**")
                if c2.button("✕", key=f"del_{ticker}"):
                    db.remove_from_watchlist(ticker)
                    st.session_state.watchlist = db.get_watchlist()
                    st.rerun()
        else:
            st.info("Watchlist is empty.")

    # Example watchlist
    st.markdown("---")
    st.subheader("Quick Start — Load Example Watchlist")
    example = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "JPM"]
    st.write(f"Example: {', '.join(example)}")
    if st.button("Load Example Watchlist"):
        for ticker in example:
            db.add_to_watchlist(ticker, ticker)
        st.session_state.watchlist = db.get_watchlist()
        st.success("Example watchlist loaded! Click Refresh to fetch prices.")
        st.rerun()

# ─── Page: Weekly Report ──────────────────────────────────────────────────────
elif page == "📊 Weekly Report":
    st.title("📊 Weekly Report")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("📄 Generate Report Now", use_container_width=True):
            with st.spinner("Generating report..."):
                report = reporter.generate_weekly_report(st.session_state.watchlist)
                if report:
                    st.session_state.weekly_report = report

        if st.button("💾 Export to HTML", use_container_width=True):
            path = reporter.export_html(st.session_state.get("weekly_report", {}))
            if path:
                with open(path, "r") as f:
                    st.download_button("Download HTML", f.read(), file_name="weekly_report.html", mime="text/html")

        if st.button("📊 Export to CSV", use_container_width=True):
            path = reporter.export_csv(st.session_state.get("weekly_report", {}))
            if path:
                with open(path, "rb") as f:
                    st.download_button("Download CSV", f.read(), file_name="weekly_report.csv", mime="text/csv")

    report = st.session_state.get("weekly_report")
    if not report:
        st.info("Click 'Generate Report Now' to create your weekly summary.")
    else:
        # Summary metrics
        summary = report.get("summary", {})
        col1, col2, col3 = st.columns(3)
        col1.metric("Best Performer", summary.get("best_ticker", "N/A"),
                   delta=f"{summary.get('best_return', 0):+.2f}%")
        col2.metric("Worst Performer", summary.get("worst_ticker", "N/A"),
                   delta=f"{summary.get('worst_return', 0):+.2f}%", delta_color="inverse")
        col3.metric("Avg Weekly Return", f"{summary.get('avg_return', 0):+.2f}%")

        st.markdown("---")

        # Ranked table
        st.subheader("Performance Rankings")
        rankings = report.get("rankings", [])
        if rankings:
            df_rank = pd.DataFrame(rankings)
            # Color code
            def color_return(val):
                color = "#00d4aa" if val > 0 else "#ff4757"
                return f"color: {color}"
            st.dataframe(
                df_rank.style.applymap(color_return, subset=["Weekly Return %"]),
                use_container_width=True, hide_index=True
            )

        st.markdown("---")

        # Per-stock breakdown
        st.subheader("Stock-by-Stock Breakdown")
        stocks = report.get("stocks", {})
        for ticker, data in stocks.items():
            with st.expander(f"**{ticker}** — {data.get('company_name', '')}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Week Open", f"${data.get('week_open', 0):,.2f}")
                c2.metric("Week Close", f"${data.get('week_close', 0):,.2f}")
                c3.metric("Week High", f"${data.get('week_high', 0):,.2f}")
                c4.metric("Week Low", f"${data.get('week_low', 0):,.2f}")

                c5, c6, c7 = st.columns(3)
                ret = data.get("weekly_return_pct", 0)
                c5.metric("Weekly Return", f"{ret:+.2f}%", delta=ret)
                c6.metric("Avg Daily Volume", f"{data.get('avg_volume', 0)/1e6:.2f}M")
                c7.metric("Trend", data.get("trend", "Neutral"))

# ─── Page: Alerts ─────────────────────────────────────────────────────────────
elif page == "🔔 Alerts":
    st.title("🔔 Price Alerts")

    watchlist = st.session_state.watchlist

    # Add new alert
    st.subheader("Add Alert")
    c1, c2, c3, c4 = st.columns(4)
    alert_ticker = c1.selectbox("Ticker", watchlist if watchlist else ["—"])
    alert_type = c2.selectbox("Type", ["Price Above", "Price Below", "Daily Move >", "Volume Spike >"])
    alert_value = c3.number_input("Threshold", min_value=0.0, value=100.0, step=1.0)
    if c4.button("➕ Add Alert", use_container_width=True):
        alerts.add_alert(alert_ticker, alert_type, alert_value)
        st.success(f"Alert added: {alert_ticker} — {alert_type} {alert_value}")
        st.rerun()

    st.markdown("---")

    # Current alerts
    st.subheader("Active Alerts")
    all_alerts = alerts.get_all_alerts()
    if all_alerts:
        for a in all_alerts:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
            c1.markdown(f"**{a['ticker']}**")
            c2.write(a['alert_type'])
            c3.write(f"Threshold: {a['threshold']}")
            status = "🟢 Active" if a['active'] else "⚫ Inactive"
            c4.write(status)
            if c5.button("✕", key=f"del_alert_{a['id']}"):
                alerts.delete_alert(a['id'])
                st.rerun()
    else:
        st.info("No alerts set. Add one above.")

    st.markdown("---")

    # Check alerts against latest prices
    st.subheader("Alert Check")
    if st.button("🔍 Check All Alerts Now"):
        latest = db.get_latest_prices(watchlist)
        triggered = alerts.check_alerts(latest)
        if triggered:
            for t in triggered:
                st.warning(f"🚨 **{t['ticker']}**: {t['message']}")
        else:
            st.success("No alerts triggered.")

# ─── Page: Settings ───────────────────────────────────────────────────────────
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.subheader("Scheduler Configuration")
    st.info("The scheduler runs automatically when you start the app. Configure timing below.")

    c1, c2 = st.columns(2)
    fetch_time = c1.time_input("Daily fetch time (market close)", value=datetime.strptime("16:30", "%H:%M").time())
    report_day = c2.selectbox("Weekly report day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], index=4)

    if st.button("💾 Save Schedule"):
        db.save_setting("fetch_time", str(fetch_time))
        db.save_setting("report_day", report_day)
        st.success("Schedule saved!")

    st.markdown("---")
    st.subheader("Email Notifications (Optional)")
    email_addr = st.text_input("Email address for weekly reports", placeholder="you@example.com")
    smtp_host = st.text_input("SMTP host", placeholder="smtp.gmail.com")
    smtp_port = st.number_input("SMTP port", value=587)
    smtp_user = st.text_input("SMTP username")
    smtp_pass = st.text_input("SMTP password", type="password")

    if st.button("💾 Save Email Settings"):
        db.save_setting("email", email_addr)
        db.save_setting("smtp_host", smtp_host)
        db.save_setting("smtp_port", str(smtp_port))
        db.save_setting("smtp_user", smtp_user)
        db.save_setting("smtp_pass", smtp_pass)
        st.success("Email settings saved!")

    st.markdown("---")
    st.subheader("Benchmark Comparison")
    benchmark = st.selectbox("Compare against", ["^GSPC (S&P 500)", "^DJI (Dow Jones)", "^IXIC (NASDAQ)", "None"])
    if st.button("Save Benchmark"):
        db.save_setting("benchmark", benchmark)
        st.success("Benchmark saved!")

    st.markdown("---")
    st.subheader("Database")
    if st.button("🗑️ Clear All Historical Data", type="secondary"):
        if st.checkbox("I confirm I want to delete all data"):
            db.clear_all_data()
            st.warning("All data cleared.")

# Auto refresh every 5 minutes
import time
time.sleep(300)
st.rerun()
