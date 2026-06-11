# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── SMS PROVIDER ─────────────────────────────────────────────
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "test")

# ── AFRICA'S TALKING ─────────────────────────────────────────
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY  = os.getenv("AT_API_KEY", "")

# ── TWILIO (backup) ──────────────────────────────────────────
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# ── DATABASE ─────────────────────────────────────────────────
DATABASE_PATH = "data/awareness.db"
DB_KEY        = os.getenv("DB_KEY", "")

# ── LANGUAGE ─────────────────────────────────────────────────
DEFAULT_LANGUAGE = "english"

# ── SCHEDULE ─────────────────────────────────────────────────
AWARENESS_FREQUENCY  = "daily"
AWARENESS_HOUR       = 9
AWARENESS_MINUTE     = 8
WARNING_CHECK_HOUR   = 8
WARNING_CHECK_MINUTE = 0

# ── TEST MODE ────────────────────────────────────────────────
TEST_MODE = os.getenv("TEST_MODE", "True") == "True"