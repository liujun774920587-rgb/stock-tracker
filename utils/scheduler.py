"""
utils/scheduler.py
Background scheduler using APScheduler.
- Fetches prices daily at market close (4:30 PM ET weekdays)
- Generates weekly report every Friday at 5 PM ET
Runs in a daemon thread so it doesn't block Streamlit.
"""

import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# APScheduler is optional — if not installed the app still works manually
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Automatic scheduling disabled.")


class SchedulerManager:
    """
    Wraps APScheduler to provide automatic daily price fetching
    and weekly report generation.
    """

    def __init__(self, fetcher, db, reporter):
        self.fetcher = fetcher
        self.db = db
        self.reporter = reporter
        self._scheduler = None
        self._lock = threading.Lock()

    def start(self):
        """Start the background scheduler (call once at app startup)."""
        if not SCHEDULER_AVAILABLE:
            logger.info("Scheduler not available — skipping.")
            return
        with self._lock:
            if self._scheduler and self._scheduler.running:
                return
            self._scheduler = BackgroundScheduler(timezone="America/New_York")

            # Daily fetch: weekdays at 4:31 PM ET (just after market close)
            self._scheduler.add_job(
                self._daily_fetch,
                CronTrigger(day_of_week="mon-fri", hour=16, minute=31),
                id="daily_fetch",
                replace_existing=True
            )

            # Weekly report: Fridays at 5:00 PM ET
            self._scheduler.add_job(
                self._weekly_report,
                CronTrigger(day_of_week="fri", hour=17, minute=0),
                id="weekly_report",
                replace_existing=True
            )

            self._scheduler.start()
            logger.info("Scheduler started — daily fetch at 4:31 PM ET, weekly report Fridays 5 PM ET.")

    def stop(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def _daily_fetch(self):
        """Fetch and store today's prices for all watchlist tickers."""
        logger.info(f"[Scheduler] Daily fetch starting at {datetime.now()}")
        tickers = self.db.get_watchlist()
        if not tickers:
            return
        results = self.fetcher.fetch_all(tickers)
        saved = 0
        for ticker, data in results.items():
            if data:
                self.db.save_daily_data(ticker, data)
                saved += 1
        logger.info(f"[Scheduler] Daily fetch complete — saved {saved}/{len(tickers)} stocks.")

    def _weekly_report(self):
        """Generate and save the weekly report."""
        logger.info(f"[Scheduler] Weekly report generating at {datetime.now()}")
        tickers = self.db.get_watchlist()
        if not tickers:
            return
        report = self.reporter.generate_weekly_report(tickers)
        if report:
            html_path = self.reporter.export_html(report)
            csv_path = self.reporter.export_csv(report)
            self.reporter.print_report(report)
            logger.info(f"[Scheduler] Weekly report saved: {html_path}, {csv_path}")

            # Optional email
            self._maybe_email_report(html_path)

    def _maybe_email_report(self, html_path: str):
        """Send the report by email if SMTP settings are configured."""
        email = self.db.get_setting("email")
        smtp_host = self.db.get_setting("smtp_host")
        if not email or not smtp_host:
            return
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders

            smtp_port = int(self.db.get_setting("smtp_port", "587"))
            smtp_user = self.db.get_setting("smtp_user")
            smtp_pass = self.db.get_setting("smtp_pass")

            msg = MIMEMultipart()
            msg["Subject"] = f"📈 Weekly Stock Report — {datetime.now().strftime('%B %d, %Y')}"
            msg["From"] = smtp_user
            msg["To"] = email
            msg.attach(MIMEText("Your weekly stock report is attached.", "plain"))

            if html_path:
                with open(html_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename=weekly_report.html")
                    msg.attach(part)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, email, msg.as_string())

            logger.info(f"Weekly report emailed to {email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
