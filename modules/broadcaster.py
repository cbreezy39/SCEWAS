# modules/broadcaster.py
# ─────────────────────────────────────────────────────────────
# EARLY WARNING BROADCASTER
#
# This module is the heart of the Early Warning System.
# It handles two types of broadcasts:
#
#   1. ALERT BROADCAST
#      Immediately sends active high-priority alerts to all users.
#      Called when a new alert is created OR by the scheduled
#      warning check that runs every morning.
#
#   2. AWARENESS BROADCAST
#      Sends the next scheduled awareness tip to all users.
#      Called by the daily/weekly scheduler.
#
# Both broadcasts use the hybrid translation module to send
# messages in each user's preferred language.
# ─────────────────────────────────────────────────────────────

import time
import datetime
from modules.database import (
    get_active_users, get_next_tip, mark_tip_sent,
    get_active_alerts, mark_alert_broadcast, log_send
)
from modules.translator import translate_tip, translate_alert
from modules.sms_sender import send_sms


# ── ALERT BROADCAST ──7────────────────────────────────────────

def broadcast_alerts():
    """
    Sends all currently active alerts to every registered user.

    This is what makes the system an EARLY WARNING system.
    When a scam is detected and an alert is created, this
    function fires immediately and gets the warning out to
    all users in their own language.

    Called:
      - Immediately when a new alert is added via the admin menu
      - Every morning by the scheduled warning check
    """
    alerts = get_active_alerts()

    if not alerts:
        print("[Broadcaster] No active alerts at this time.")
        return

    users = get_active_users()
    if not users:
        print("[Broadcaster] No active users registered.")
        return

    print(f"\n[Broadcaster] ALERT BROADCAST — {len(alerts)} active alert(s), {len(users)} user(s)")
    print(f"[Broadcaster] Time: {datetime.datetime.now()}\n")

    for alert in alerts:
        print(f"  Broadcasting alert ID={alert['id']} | Severity={alert['severity']} | Category={alert['category']}")

        success_count = 0
        fail_count    = 0

        for user in users:
            # Translate alert to user's preferred language
            message = translate_alert(alert, user["language"])

            # Send the SMS
            result = send_sms(user["phone"], message, message_type="alert")

            # Log the send
            status = "sent" if result["success"] else "failed"
            log_send(user["id"], alert["id"], user["language"],
                     message_type="alert", status=status)

            if result["success"]:
                success_count += 1
            else:
                fail_count += 1

                time.sleep(5.0)  # Rate limit: 5 second between failed sends to avoid overwhelming the provider

        # Update broadcast counter for this alert
        mark_alert_broadcast(alert["id"])

        print(f"  Alert {alert['id']} broadcast complete — Sent: {success_count}, Failed: {fail_count}")

    print(f"\n[Broadcaster] Alert broadcast finished.\n")


#AWARENESS BROADCAST 

def broadcast_awareness():
    """
    Sends the next scheduled awareness tip to all users.

    Uses round-robin tip selection — always picks the tip
    with the lowest sent_count so all tips are distributed
    evenly before any are repeated.

    Called automatically by the scheduler at the configured
    daily or weekly time.
    """
    print(f"\n[Broadcaster] AWARENESS BROADCAST — {datetime.datetime.now()}")

    # Get the next tip
    tip = get_next_tip()
    if not tip:
        print("[Broadcaster] No tips found. Please seed the database.")
        return

    print(f"  Tip ID={tip['id']} | Category={tip['category']}")

    users = get_active_users()
    if not users:
        print("[Broadcaster] No active users.")
        return

    success_count = 0
    fail_count    = 0

    for user in users:
        # Convert SQLite Row to dict for translator
        tip_dict = {
            "english": tip["english"],
            "bemba":   tip["bemba"] or "",
            "nyanja":  tip["nyanja"] or ""
        }
        message = translate_tip(tip_dict, user["language"])
        result  = send_sms(user["phone"], message, message_type="awareness")

        status = "sent" if result["success"] else "failed"
        log_send(user["id"], tip["id"], user["language"],
                 message_type="awareness", status=status)

        if result["success"]:
            success_count += 1
        else:
            fail_count += 1

            time.sleep(5.0) 

    mark_tip_sent(tip["id"])

    print(f"  Awareness blast complete — Sent: {success_count}, Failed: {fail_count}\n")


# ── COMBINED DAILY BROADCAST ──────────────────────────────────

def daily_broadcast():
    """
    The full daily broadcast sequence:
      1. Check for active alerts first — send any warnings
      2. Then send the scheduled awareness tip

    This is what the scheduler calls every day.
    Alerts always go before awareness tips so urgent
    warnings reach users as early as possible.
    """
    print("\n" + "=" * 60)
    print(f"  DAILY BROADCAST  —  {datetime.datetime.now().strftime('%A %d %B %Y  %H:%M')}")
    print("=" * 60)

    # Step 1: Early warnings first
    broadcast_alerts()

    # Step 2: Scheduled awareness tip
    broadcast_awareness()

    print("=" * 60 + "\n")
