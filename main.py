# main.py
# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
#
# Design of a Low-Cost, Local-Language SMS Cybersecurity
# Early Warning and Public Awareness Infrastructure for
# Rural and Low-Connectivity Areas
#
# Author  : Charmaine Isabel Lawrence
# Student : 202201770
# Program : BSc Cyber Security — ZCAS University
# ─────────────────────────────────────────────────────────────

import os
import sys

# Ensure UTF-8 console output so the box-drawing / em-dash characters used
# throughout the menus render on Windows (default cp1252 raises
# UnicodeEncodeError). Harmless on macOS/Linux, which are already UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

# Force Python's requests library to bypass any environment adapters for AT
os.environ['no_proxy'] = 'api.sandbox.africastalking.com,sandbox.africastalking.com,africastalking.com'
from modules.database import create_tables, add_user, add_tip, get_send_stats
from modules.tips import TIPS, SAMPLE_ALERTS
from modules.broadcaster import broadcast_alerts, broadcast_awareness, daily_broadcast
from modules.scheduler import start_scheduler
from modules.admin import admin_menu
from modules.translator import translate_tip
from config import TEST_MODE


def seed_database():
    """
    Loads initial tips and sample alerts into the database.
    Run only once — data persists in data/awareness.db.
    """
    from modules.database import get_connection    
    conn = get_connection()
    already_seeded = conn.execute(
        "SELECT COUNT(*) FROM tips"
    ).fetchone()[0]
    conn.close()

    if already_seeded > 0:
        print("[Setup] Database already seeded — skipping.")
        return

    print("\n[Setup] Seeding database for first time...")

    for tip in TIPS:
        add_tip(
            category=tip["category"],
            english=tip["english"],
            bemba=tip.get("bemba", ""),
            nyanja=tip.get("nyanja", "")
        )

    # Load sample early warning alerts
    from modules.database import add_alert
    for alert in SAMPLE_ALERTS:
        add_alert(
            category=alert["category"],
            english=alert["english"],
            bemba=alert.get("bemba", ""),
            nyanja=alert.get("nyanja", ""),
            severity=alert["severity"]
        )

    # Register sample test users
    
    add_user("Test User",   "+260900000000", language="English",  area="Lusaka")
   

    
    print("[Setup] Seeding complete.\n")


def show_status():
    """Prints a system status summary."""
    from modules.database import get_active_users, get_active_alerts, list_all_alerts
    users  = get_active_users()
    active = get_active_alerts()
    stats  = get_send_stats()

    print("\n" + "=" * 60)
    print("  LOW-COST LOCAL-LANGUAGE SMS CYBERSECURITY SYSTEM")
    print("  Early Warning & Public Awareness Infrastructure")
    print("=" * 60)
    print(f"  Mode           : {'TEST (no real SMS)' if TEST_MODE else 'LIVE'}")
    print(f"  Active users   : {len(users)}")
    print(f"  Active alerts  : {len(active)}")
    print(f"  Tips loaded    : {len(TIPS)}")

    if active:
        print(f"\n   ACTIVE ALERTS:")
        for a in active:
            print(f"     [{a['severity']}] {a['category']} — {a['english'][:60]}...")

    if stats:
        print(f"\n  Send History:")
        for s in stats:
            print(f"     {s['message_type']:<12} {s['language']:<10} {s['total_sent']} messages sent")
    else:
        print(f"\n  No messages sent yet.")
    print("=" * 60 + "\n")


def demo_translations():
    """Shows the hybrid translation working across all 3 languages."""
    print("\n[Demo] Translation Preview (Alert 1):")
    print("─" * 60)
    sample = SAMPLE_ALERTS[0]
    for lang in ["english", "bemba", "nyanja"]:
        text = translate_tip(sample, lang)
        print(f"\n  [{lang.upper()}]")
        print(f"  {text}")
    print("─" * 60 + "\n")


# ─────────────────────────────────────────────────────────────
#  START
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  SMS CYBERSECURITY EARLY WARNING & AWARENESS SYSTEM")
    print("  Charmaine Isabel Lawrence  |  202201770")
    print("  ZCAS University  |  BSc Cyber Security")
    print("=" * 60)

    # Initialise database
    create_tables()
    seed_database()
    show_status()
    demo_translations()

    # Main menu
    while True:
        print("\nMAIN MENU")
        print("─" * 40)
        print("  1  Send AWARENESS tip now (test blast)")
        print("  2  Send ALERT broadcast now (manual trigger)")
        print("  3  Run FULL daily broadcast (alerts + awareness)")
        print("  4  Start SCHEDULER (automated daily/weekly)")
        print("  5  Open ADMIN panel (manage alerts & users)")
        print("  6  View system status")
        print("  7  Exit")
        print("─" * 40)

        choice = input("  Enter choice (1–7): ").strip()

        if choice == "1":
            broadcast_awareness()
        elif choice == "2":
            broadcast_alerts()
        elif choice == "3":
            daily_broadcast()
        elif choice == "4":
            start_scheduler()
        elif choice == "5":
            admin_menu()
        elif choice == "6":
            show_status()
        elif choice == "7":
            print("\n  Goodbye!\n")
            break
        else:
            print("  Invalid choice — enter a number 1–7.")
