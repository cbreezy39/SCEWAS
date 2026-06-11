# modules/admin.py
# ─────────────────────────────────────────────────────────────
# ADMIN MENU
#
# This is the operator's control panel.
# From here you can:
#   - Create a new early warning alert (broadcasts immediately)
#   - View all active and past alerts
#   - Resolve (deactivate) an alert
#   - Register new users
#   - View send statistics
#
# This runs inside main.py when the operator chooses
# the Admin / Alert Management option.
# ─────────────────────────────────────────────────────────────

from modules.database import (
    add_alert, get_active_alerts, list_all_alerts,
    resolve_alert, add_user, get_active_users, get_send_stats
)
from modules.broadcaster import broadcast_alerts


def admin_menu():
    """Main admin menu loop."""
    while True:
        print("\n" + "─" * 50)
        print("  ADMIN PANEL — Early Warning & Awareness System")
        print("─" * 50)
        print("  1  Create new early warning ALERT  (broadcasts immediately)")
        print("  2  View active alerts")
        print("  3  View all alerts (including resolved)")
        print("  4  Resolve an alert (stop broadcasting it)")
        print("  5  Broadcast active alerts NOW (manual trigger)")
        print("  6  Register a new user")
        print("  7  View all registered users")
        print("  8  View send statistics")
        print("  9  Back to main menu")
        print("─" * 50)

        choice = input("  Enter choice: ").strip()

        if choice == "1":
            _create_alert()
        elif choice == "2":
            _view_active_alerts()
        elif choice == "3":
            _view_all_alerts()
        elif choice == "4":
            _resolve_alert()
        elif choice == "5":
            print("\n[Admin] Broadcasting active alerts NOW...")
            broadcast_alerts()
        elif choice == "6":
            _register_user()
        elif choice == "7":
            _view_users()
        elif choice == "8":
            _view_stats()
        elif choice == "9":
            break
        else:
            print("  Invalid choice.")


def _create_alert():
    """Guides the operator through creating a new alert."""
    print("\n  CREATE NEW EARLY WARNING ALERT")
    print("  (This will be broadcast immediately to all users)\n")

    # Category
    print("  Categories: smishing | mobile_money | vishing | phishing | general")
    category = input("  Category: ").strip().lower() or "general"

    # Severity
    print("  Severity:  HIGH (immediate threat) | MEDIUM (emerging) | LOW (advisory)")
    severity = input("  Severity [HIGH]: ").strip().upper() or "HIGH"
    if severity not in ("HIGH", "MEDIUM", "LOW"):
        severity = "HIGH"

    # English message
    print(f"\n  Write the alert message in English (keep under 160 characters):")
    english = input("  English: ").strip()
    if not english:
        print("  Alert message cannot be empty.")
        return

    print(f"  Characters: {len(english)}/160")
    if len(english) > 160:
        print("  WARNING: Message exceeds 160 chars — it will split into multiple SMS.")

    # Bemba translation
    print(f"\n  Bemba translation (press Enter to leave blank — glossary will be used):")
    bemba = input("  Bemba: ").strip()

    # Nyanja translation
    print(f"\n  Nyanja translation (press Enter to leave blank):")
    nyanja = input("  Nyanja: ").strip()

    # Expiry
    print(f"\n  Expiry datetime (e.g. 2026-05-10 23:59:00) or press Enter for no expiry:")
    expires_at = input("  Expires at: ").strip() or None

    # Confirm
    print(f"\n  ── Preview ──────────────────────────────────")
    print(f"  Category : {category}")
    print(f"  Severity : {severity}")
    print(f"  English  : {english}")
    if bemba:   print(f"  Bemba    : {bemba}")
    if nyanja:  print(f"  Nyanja   : {nyanja}")
    if expires_at: print(f"  Expires  : {expires_at}")
    print(f"  ─────────────────────────────────────────────")

    confirm = input("\n  Broadcast this alert now? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Alert cancelled.")
        return

    add_alert(category, english, bemba, nyanja, severity, expires_at)
    print(f"\n  Alert created. Broadcasting to all users now...")
    broadcast_alerts()


def _view_active_alerts():
    alerts = get_active_alerts()
    if not alerts:
        print("\n  No active alerts.")
        return
    print(f"\n  ACTIVE ALERTS ({len(alerts)}):")
    print(f"  {'ID':<5} {'Severity':<10} {'Category':<15} {'Broadcasts':<12} {'Created'}")
    print("  " + "-" * 65)
    for a in alerts:
        print(f"  {a['id']:<5} {a['severity']:<10} {a['category']:<15} {a['broadcast_count']:<12} {a['created_at']}")
        print(f"    EN: {a['english'][:70]}...")


def _view_all_alerts():
    alerts = list_all_alerts()
    if not alerts:
        print("\n  No alerts found.")
        return
    print(f"\n  ALL ALERTS ({len(alerts)}):")
    print(f"  {'ID':<5} {'Active':<8} {'Severity':<10} {'Category':<15} {'Created'}")
    print("  " + "-" * 65)
    for a in alerts:
        status = "ACTIVE" if a["active"] else "resolved"
        print(f"  {a['id']:<5} {status:<8} {a['severity']:<10} {a['category']:<15} {a['created_at']}")


def _resolve_alert():
    _view_active_alerts()
    alert_id = input("\n  Enter alert ID to resolve (or Enter to cancel): ").strip()
    if alert_id.isdigit():
        resolve_alert(int(alert_id))
        print(f"  Alert {alert_id} resolved — it will no longer be broadcast.")
    else:
        print("  Cancelled.")


def _register_user():
    print("\n  REGISTER NEW USER")
    name     = input("  Name: ").strip()
    phone    = input("  Phone (e.g. +260977123456): ").strip()
    print("  Language options: english | bemba | nyanja")
    language = input("  Language [english]: ").strip().lower() or "english"
    area     = input("  Area/District (e.g. Chipata, Kabwe): ").strip() or "unknown"

    if not phone.startswith("+"):
        print("  Phone must start with + and country code (e.g. +260 for Zambia)")
        return

    add_user(name, phone, language, area)


def _view_users():
    users = get_active_users()
    if not users:
        print("\n  No active users.")
        return
    print(f"\n  REGISTERED USERS ({len(users)}):")
    print(f"  {'ID':<5} {'Name':<20} {'Phone':<18} {'Language':<10} {'Area'}")
    print("  " + "-" * 70)
    for u in users:
        print(f"  {u['id']:<5} {u['name']:<20} {u['phone']:<18} {u['language']:<10} {u['area']}")


def _view_stats():
    stats = get_send_stats()
    if not stats:
        print("\n  No messages sent yet.")
        return
    print(f"\n  SEND STATISTICS:")
    print(f"  {'Type':<12} {'Language':<10} {'Total Sent':<12} {'Users Reached':<15} {'Last Sent'}")
    print("  " + "-" * 70)
    for s in stats:
        print(f"  {s['message_type']:<12} {s['language']:<10} {s['total_sent']:<12} {s['unique_users']:<15} {s['last_sent']}")
