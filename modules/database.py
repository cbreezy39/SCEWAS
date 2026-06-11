# modules/database.py
# ─────────────────────────────────────────────────────────────
# DATABASE MODULE
#
# Tables:
#   users      — registered recipients (phone, language, area)
#   tips       — scheduled awareness tips (EN/Bemba/Nyanja)
#   alerts     — early warning alerts (urgent, manual or timed)
#   send_log   — full record of every SMS sent
#
# NEW in this version:
#   The alerts table is what makes this an Early Warning System.
#   An alert has a severity level (HIGH/MEDIUM/LOW), a category
#   (e.g. smishing, mobile_money), and an active flag.
#   When active, the system broadcasts it immediately to all users.
# ─────────────────────────────────────────────────────────────

import sqlite3
import os
from config import DATABASE_PATH

import os
from cryptography.fernet import Fernet
from config import DB_KEY

# Create cipher using the DB_KEY from .env
# DB_KEY must be a valid Fernet key — we derive one from your string
import base64
import hashlib

def get_cipher():
    # Convert your DB_KEY string into a valid 32-byte Fernet key
    key = hashlib.sha256(DB_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt_phone(phone: str) -> str:
    """Encrypts a phone number before storing in database."""
    cipher = get_cipher()
    return cipher.encrypt(phone.encode()).decode()

def decrypt_phone(encrypted_phone: str) -> str:
    """Decrypts a phone number when retrieved from database."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_phone.encode()).decode()

def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Creates all tables on first run."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── USERS ────────────────────────────────────────────────
    # area = rural district/town — useful for your dissertation
    # (shows the system is designed for specific communities)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            phone      TEXT    NOT NULL UNIQUE,
            language   TEXT    NOT NULL DEFAULT 'english',
            area       TEXT    DEFAULT 'unknown',
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── TIPS ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tips (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            category   TEXT NOT NULL,
            english    TEXT NOT NULL,
            bemba      TEXT,
            nyanja     TEXT,
            sent_count INTEGER DEFAULT 0
        )
    """)

    # ── ALERTS ───────────────────────────────────────────────
    # This is the EARLY WARNING table — new in this version.
    #
    # severity : HIGH   = immediate threat (broadcast now)
    #            MEDIUM = active scam (broadcast today)
    #            LOW    = advisory notice
    #
    # active   : 1 = currently broadcasting | 0 = resolved
    #
    # broadcast_count : how many times this alert has been sent
    #
    # expires_at : when the alert automatically deactivates
    #              NULL = stays active until manually resolved
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category        TEXT    NOT NULL,
            severity        TEXT    NOT NULL DEFAULT 'HIGH',
            english         TEXT    NOT NULL,
            bemba           TEXT,
            nyanja          TEXT,
            active          INTEGER NOT NULL DEFAULT 1,
            broadcast_count INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now')),
            expires_at      TEXT    DEFAULT NULL
        )
    """)

    # ── SEND LOG ─────────────────────────────────────────────
    # message_type: "awareness" or "alert"
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS send_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            message_id   INTEGER NOT NULL,
            message_type TEXT    NOT NULL DEFAULT 'awareness',
            language     TEXT    NOT NULL,
            sent_at      TEXT    DEFAULT (datetime('now')),
            status       TEXT    DEFAULT 'sent'
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] All tables ready.")


# ── USER FUNCTIONS ────────────────────────────────────────────

def add_user(name, phone, language="english", area="unknown"):
    conn = get_connection()
    try:
        encrypted = encrypt_phone(phone)
        conn.execute(
            "INSERT INTO users (name, phone, language, area) VALUES (?, ?, ?, ?)",
            (name, encrypted, language, area)
        )
        conn.commit()
        print(f"[DB] User registered: {name} | {language} | {area}")
    except sqlite3.IntegrityError:
        print(f"[DB] User with that number already registered.")
    finally:
        conn.close()


def get_active_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users WHERE active = 1").fetchall()
    conn.close()
    
    # Decrypt phone numbers before returning
    users = []
    for row in rows:
        user = dict(row)
        try:
            user["phone"] = decrypt_phone(user["phone"])
        except Exception:
            # If decryption fails phone is already plain text
            pass
        users.append(user)
    return users


# ── TIP FUNCTIONS ─────────────────────────────────────────────

def add_tip(category, english, bemba="", nyanja=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO tips (category, english, bemba, nyanja) VALUES (?, ?, ?, ?)",
        (category, english, bemba, nyanja)
    )
    conn.commit()
    conn.close()


def get_next_tip():
    """Round-robin: always picks the least-sent tip."""
    conn = get_connection()
    tip = conn.execute(
        "SELECT * FROM tips ORDER BY sent_count ASC, id ASC LIMIT 1"
    ).fetchone()
    conn.close()
    return tip


def mark_tip_sent(tip_id):
    conn = get_connection()
    conn.execute("UPDATE tips SET sent_count = sent_count + 1 WHERE id = ?", (tip_id,))
    conn.commit()
    conn.close()


# ── ALERT FUNCTIONS ───────────────────────────────────────────

def add_alert(category, english, bemba="", nyanja="",
              severity="HIGH", expires_at=None):
    """
    Creates a new early warning alert.

    severity options:
      HIGH   — active scam right now (e.g. mass smishing attack)
      MEDIUM — emerging threat (e.g. new fraud method spotted)
      LOW    — advisory (e.g. general reminder during festive season)

    expires_at — datetime string e.g. "2026-05-10 23:59:00"
                 After this time the alert auto-deactivates.
                 Pass None for indefinite.

    Example:
        add_alert(
            category  = "smishing",
            severity  = "HIGH",
            english   = "WARNING: Fraudsters are sending fake Airtel prize messages today...",
            bemba     = "ICEBO: Abafyenyi batuma ubutumwa bwa Airtel bwa bupuba lelo...",
            nyanja    = "CHENJERANI: Achinyengo akutumiza mauthenga onama a Airtel lero..."
        )
    """
    conn = get_connection()
    conn.execute(
        """INSERT INTO alerts
           (category, severity, english, bemba, nyanja, active, expires_at)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (category, severity.upper(), english, bemba, nyanja, expires_at)
    )
    conn.commit()
    conn.close()
    print(f"[DB] Alert created: [{severity.upper()}] {category}")


def get_active_alerts():
    """
    Returns all alerts that are currently active.
    Also auto-expires any alerts past their expiry time.
    """
    conn = get_connection()
    # Auto-expire alerts that have passed their expiry time
    conn.execute("""
        UPDATE alerts SET active = 0
        WHERE active = 1
        AND expires_at IS NOT NULL
        AND datetime(expires_at) < datetime('now')
    """)
    conn.commit()
    alerts = conn.execute(
        "SELECT * FROM alerts WHERE active = 1 ORDER BY severity ASC, created_at ASC"
    ).fetchall()
    conn.close()
    return alerts


def resolve_alert(alert_id):
    """Marks an alert as resolved (stops broadcasting it)."""
    conn = get_connection()
    conn.execute("UPDATE alerts SET active = 0 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    print(f"[DB] Alert {alert_id} resolved.")


def mark_alert_broadcast(alert_id):
    """Increments how many times this alert has been broadcast."""
    conn = get_connection()
    conn.execute(
        "UPDATE alerts SET broadcast_count = broadcast_count + 1 WHERE id = ?",
        (alert_id,)
    )
    conn.commit()
    conn.close()


def list_all_alerts():
    """Returns all alerts (active and resolved) for the admin view."""
    conn = get_connection()
    alerts = conn.execute(
        "SELECT * FROM alerts ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return alerts


# ── LOG FUNCTIONS ─────────────────────────────────────────────

def log_send(user_id, message_id, language, message_type="awareness", status="sent"):
    conn = get_connection()
    conn.execute(
        """INSERT INTO send_log (user_id, message_id, message_type, language, status)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, message_id, message_type, language, status)
    )
    conn.commit()
    conn.close()


def get_send_stats():
    """Summary of all messages sent — for evaluation chapter."""
    conn = get_connection()
    stats = conn.execute("""
        SELECT
            message_type,
            language,
            COUNT(*)             AS total_sent,
            COUNT(DISTINCT user_id) AS unique_users,
            MIN(sent_at)         AS first_sent,
            MAX(sent_at)         AS last_sent
        FROM send_log
        GROUP BY message_type, language
        ORDER BY message_type, language
    """).fetchall()
    conn.close()
    return stats
