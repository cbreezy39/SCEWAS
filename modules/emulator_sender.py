# modules/emulator_sender.py
# ─────────────────────────────────────────────────────────────
# EMULATOR SMS INJECTION  —  local, fee-free delivery for demos
#
# Lets the system deliver a message into a running Android
# emulator's inbox so it appears on-screen, with no carrier,
# no SIM, and no cost.  Active only when:
#     TEST_MODE=True   and   TEST_TARGET=emulator
#
# Two delivery methods (config: EMULATOR_METHOD):
#
#   "emu"     adb emu sms send <from> <text>
#             Android Studio AVD only. Injects through the
#             telephony stack as a REAL inbound SMS. Most
#             reliable. Sender id must be numeric.
#
#   "content" adb shell content insert ... content://sms/inbox
#             + SMS_RECEIVED broadcast. The guide's method.
#             Works on older / permissive Genymotion images,
#             but is BLOCKED on Android 4.4+ (only the default
#             SMS app may write to the SMS provider).
#
# No extra pip dependency — shells out to the adb in platform-tools.
# ─────────────────────────────────────────────────────────────

import shutil
import subprocess

try:
    from config import ADB_PATH, EMULATOR_METHOD, EMULATOR_SENDER_ID
except ImportError:  # allow standalone import during testing
    ADB_PATH = ""
    EMULATOR_METHOD = "emu"
    EMULATOR_SENDER_ID = "0972000000"


def _adb():
    """Resolve the adb binary (explicit ADB_PATH wins, else PATH)."""
    return ADB_PATH or shutil.which("adb")


def _run(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _online_serial():
    """Return (True, serial) for the first emulator in 'device' state."""
    adb = _adb()
    if not adb:
        return False, "adb not found — install platform-tools or set ADB_PATH in .env"
    try:
        r = _run([adb, "devices"])
    except Exception as e:
        return False, f"could not run adb: {e}"
    serials = [
        line.split("\t")[0]
        for line in r.stdout.splitlines()[1:]
        if line.strip().endswith("\tdevice")
    ]
    if not serials:
        return False, "no emulator in 'device' state — is it booted? (adb devices)"
    return True, serials[0]


def _send_via_emu(base, sender_id, message):
    # subprocess passes argv directly (no shell), so spaces are safe.
    # Commas in the body can still trip the AVD console on some images.
    r = _run(base + ["emu", "sms", "send", sender_id, message])
    blob = (r.stdout + r.stderr).upper()
    ok = r.returncode == 0 and "KO" not in blob
    return ok, (r.stdout or r.stderr).strip() or "ok"


def _send_via_content(base, sender_id, message):
    r = _run(base + [
        "shell", "content", "insert",
        "--uri", "content://sms/inbox",
        "--bind", f"address:s:{sender_id}",
        "--bind", f"body:s:{message}",
        "--bind", "read:i:0",
    ])
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip() or "content insert failed"
    # Nudge the messaging UI to redraw the new row.
    _run(base + ["shell", "am", "broadcast",
                 "-a", "android.provider.Telephony.SMS_RECEIVED"])
    return True, "inserted into content://sms/inbox"


def send_to_emulator(phone: str, message: str) -> dict:
    """
    Deliver `message` into a local emulator's inbox.

    An emulator has a single inbox, so `phone` (the real recipient) can't
    be the destination — instead EMULATOR_SENDER_ID (or `phone`) is used as
    the *sender* label of the inbound message.

    Returns {"success": bool, "detail": str}.
    """
    ok, info = _online_serial()
    if not ok:
        return {"success": False, "detail": info}

    serial = info
    base = [_adb(), "-s", serial]
    sender_id = EMULATOR_SENDER_ID or phone or "12345"
    method = (EMULATOR_METHOD or "emu").lower()

    if method == "content":
        ok, detail = _send_via_content(base, sender_id, message)
    else:
        ok, detail = _send_via_emu(base, sender_id, message)
        if not ok:  # fall back to the guide's method
            ok2, detail2 = _send_via_content(base, sender_id, message)
            if ok2:
                return {"success": True,
                        "detail": f"emu rejected ({detail}); content fallback ok"}
            detail = f"emu: {detail} | content: {detail2}"

    return {"success": ok, "detail": detail}
