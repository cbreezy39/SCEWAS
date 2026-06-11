# SCEWAS — SMS Cybersecurity Early Warning & Awareness System

A low-cost, local-language SMS system that broadcasts cybersecurity awareness
tips and early-warning alerts (English / Bemba / Nyanja) to users in rural and
low-connectivity areas. Built with Python, SQLite, and Tkinter.

It can run entirely in **test mode** (prints messages to the console — no SMS,
no cost, no accounts), deliver to a **local Android emulator** for demos, or
send **real SMS** via Africa's Talking or Twilio.

---

## Requirements

- **Python 3.10+**
- `pip` and `venv` (bundled with Python)
- *(optional)* Android SDK **platform-tools** + a booted emulator — only for
  the emulator delivery demo
- *(optional)* an Africa's Talking or Twilio account — only for sending real SMS

All Python dependencies are in [`requirements.txt`](requirements.txt).

---

## Quick start (console test mode — no accounts needed)

```bash
git clone <your-repo-url> SCEWAS
cd SCEWAS

python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt

# Create your local config from the template
cp .env.example .env        # Windows: copy .env.example .env
# Edit .env and set DB_KEY to any passphrase (see below).

python main.py
```

Choose option `1` from the menu. You should see seeded tips and translations
print, followed by a `[TEST MODE — AWARENESS]` block per user. That confirms a
working install.

> The database is created automatically at `data/awareness.db` on first run.

---

## Configuration (`.env`)

Copy `.env.example` to `.env` and fill in values. The keys you need depend on
what you want to do:

| Goal | Keys to set |
|------|-------------|
| **Run the demo** (console) | `TEST_MODE=True`, `DB_KEY=<any string>` |
| **Deliver to an emulator** | the above + `TEST_TARGET=emulator`, `ADB_PATH`, numeric `EMULATOR_SENDER_ID` |
| **Send real SMS** (Africa's Talking) | `TEST_MODE=False`, `SMS_PROVIDER=africastalking`, `AT_USERNAME`, `AT_API_KEY` |

**`DB_KEY`** — any passphrase. A Fernet encryption key is derived from it and
used to encrypt stored phone numbers. **Set it once and keep it stable**: if you
change it later, phone numbers already in the database can no longer be
decrypted.

`.env` is git-ignored — never commit it. `.env.example` documents every
available key.

---

## Emulator delivery (optional)

When `TEST_MODE=True` **and** `TEST_TARGET=emulator`, each outgoing message is
injected into a running Android emulator's inbox so it appears on-screen — no
SIM, no carrier, no cost. This shells out to `adb`; it adds no pip dependencies.

1. Boot an Android Studio AVD (or Genymotion image).
2. Confirm it is online:
   ```bash
   adb devices        # want: "emulator-5554   device"
   ```
3. In `.env` set:
   ```ini
   TEST_MODE=True
   TEST_TARGET=emulator
   EMULATOR_METHOD=emu
   EMULATOR_SENDER_ID=0972000000
   ADB_PATH=C:\path\to\platform-tools\adb.exe   # if adb isn't on PATH
   ```
4. Run `python main.py`, choose option `1`, and check the emulator's Messages
   app.

Notes:
- `EMULATOR_METHOD=emu` (`adb emu sms send`) is the reliable method for modern
  Android Studio AVDs and needs a **numeric** sender id.
- `EMULATOR_METHOD=content` is a legacy fallback for old/permissive images
  (Genymotion); it is blocked on Android 4.4+.
- If no emulator is running, delivery degrades gracefully with a clear message —
  it does not crash.

---

## Sending real SMS (optional)

Set `TEST_MODE=False` and configure a provider in `.env`:

- **Africa's Talking:** `SMS_PROVIDER=africastalking`, `AT_USERNAME`, `AT_API_KEY`
- **Twilio:** `SMS_PROVIDER=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
  `TWILIO_PHONE_NUMBER`
- **TextBelt:** `SMS_PROVIDER=textbelt` (free tier: 1 SMS/day, no account)

Use your own credentials. See [`SECURITY.md`](SECURITY.md) regarding key
rotation.

---

## Optional: ML translation (Tier-2)

The system translates via pre-written translations → glossary → English
fallback, so it works out of the box. For live NLLB-200 machine translation,
uninstall-comment the `transformers` and `torch` lines in `requirements.txt`
and reinstall. **These pull ~2.4 GB** and are not needed for normal use.

---

## Project layout

```
SCEWAS/
├── main.py            # CLI entry point (run this)
├── admingui.py        # Tkinter admin GUI (alternative entry point)
├── config.py          # reads .env; all settings live here
├── requirements.txt
├── .env.example       # config template — copy to .env
└── modules/
    ├── database.py        # SQLite + phone-number encryption
    ├── tips.py            # seed awareness tips & sample alerts
    ├── translator.py      # hybrid EN/Bemba/Nyanja translation
    ├── broadcaster.py     # sends tips/alerts to all users
    ├── scheduler.py       # automated daily/weekly broadcasts
    ├── sms_sender.py       # provider routing (AT/Twilio/TextBelt/test)
    ├── emulator_sender.py # injects SMS into a local Android emulator
    └── admin.py           # CLI admin panel
```

---

## Troubleshooting

- **`ModuleNotFoundError: No module named 'modules'`** — run from the repo root
  (`python main.py`), not from inside `modules/`.
- **Garbled or missing characters on Windows** — handled automatically;
  `main.py` reconfigures the console to UTF-8 on startup. If you run other
  scripts directly, set `PYTHONIOENCODING=utf-8`.
- **`cryptography` / `dotenv` import errors** — your virtual environment isn't
  active or dependencies aren't installed: re-run `pip install -r requirements.txt`.
