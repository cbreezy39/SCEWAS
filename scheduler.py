# modules/scheduler.py
# ─────────────────────────────────────────────────────────────
# SCHEDULER MODULE
# Manages automated daily broadcasts using APScheduler.
# ─────────────────────────────────────────────────────────────

from apscheduler.schedulers.blocking import BlockingScheduler
from modules.broadcaster import daily_broadcast
from config import (
    AWARENESS_FREQUENCY, AWARENESS_HOUR, AWARENESS_MINUTE,
    WARNING_CHECK_HOUR,  WARNING_CHECK_MINUTE
)


def start_scheduler():
    """
    Starts the automated scheduler.
    Runs until you press Ctrl+C.

    Schedule:
      - WARNING_CHECK_HOUR:MINUTE  — checks for active alerts
      - AWARENESS_HOUR:MINUTE      — sends awareness tip

    In practice the daily_broadcast() function handles both
    in sequence so they are combined into one job.
    """
    scheduler = BlockingScheduler()

    if AWARENESS_FREQUENCY == "daily":
        scheduler.add_job(
            func=daily_broadcast,
            trigger="cron",
            hour=AWARENESS_HOUR,
            minute=AWARENESS_MINUTE,
            id="daily_broadcast"
        )
        print(f"[Scheduler] Daily broadcast scheduled at {AWARENESS_HOUR:02d}:{AWARENESS_MINUTE:02d}")

    elif AWARENESS_FREQUENCY == "weekly":
        scheduler.add_job(
            func=daily_broadcast,
            trigger="cron",
            day_of_week="mon",
            hour=AWARENESS_HOUR,
            minute=AWARENESS_MINUTE,
            id="weekly_broadcast"
        )
        print(f"[Scheduler] Weekly broadcast scheduled — Mondays at {AWARENESS_HOUR:02d}:{AWARENESS_MINUTE:02d}")

    print("[Scheduler] Running. Press Ctrl+C to stop.\n")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[Scheduler] Stopped.")
        scheduler.shutdown()
