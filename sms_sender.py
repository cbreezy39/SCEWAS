# modules/sms_sender.py
# ─────────────────────────────────────────────────────────────
# SMS SENDER MODULE
# Supports Africa's Talking, Twilio, TextBelt, and Test mode.
# Provider is selected via SMS_PROVIDER in config.py.
# ─────────────────────────────────────────────────────────────

from config import SMS_PROVIDER, TEST_MODE
from config import AT_USERNAME, AT_API_KEY
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER


def send_sms(to_number: str, message: str, message_type: str = "awareness") -> dict:
    """
    Main send function. Routes to the correct provider.

    message_type: "awareness" or "alert" — used in terminal output only.
    """
    if TEST_MODE:
        tag = "ALERT" if message_type == "alert" else "AWARENESS"
        print("=" * 65)
        print(f"  [TEST MODE — {tag}]  To: {to_number}")
        print(f"  {message}")
        print("=" * 65)
        return {"success": True, "sid": "TEST"}

    provider = SMS_PROVIDER.lower()

    if provider == "africastalking":
        return _send_africastalking(to_number, message)
    elif provider == "twilio":
        return _send_twilio(to_number, message)
    elif provider == "textbelt":
        return _send_textbelt(to_number, message)
    else:
        print(f"[SMS] Unknown provider: {provider}. Set SMS_PROVIDER in config.py")
        return {"success": False, "error": "Unknown provider"}


# ── AFRICA'S TALKING ─────────────────────────────────────────
# ── AFRICA'S TALKING ─────────────────────────────────────────
def _send_africastalking(to_number: str, message: str) -> dict:
    try:
        import africastalking
        import config  # Dynamically pull config entries

        # Initialize the Africa's Talking session context
        africastalking.initialize(
            username=config.AT_USERNAME,
            api_key=config.AT_API_KEY
        )
        
        # Instantiate the SMS service component
        sms = africastalking.SMS

        # Synchronously execute the gateway broadcast
        response = sms.send(message=message, recipients=[to_number])
        print(f"[AT] Success! API Response: {response}")
        return {"success": True, "response": response}

    except ImportError:
        print("[AT] Error: SDK not found. Run: pip install africastalking")
        return {"success": False, "error": "africastalking library not installed"}
    except Exception as e:
        print(f"[AT] Error: {e}")
        return {"success": False, "error": str(e)}


# ── TWILIO ───────────────────────────────────────────────────
def _send_twilio(to_number: str, message: str) -> dict:
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_number)
        print(f"[Twilio] Sent to {to_number} | SID: {msg.sid}")
        return {"success": True, "sid": msg.sid}
    except ImportError:
        print("[Twilio] Not installed. Run: pip install twilio")
        return {"success": False, "error": "twilio not installed"}
    except Exception as e:
        print(f"[Twilio] Error: {e}")
        return {"success": False, "error": str(e)}


# ── TEXTBELT ─────────────────────────────────────────────────
def _send_textbelt(to_number: str, message: str) -> dict:
    """Free tier: 1 SMS per day. No account needed."""
    try:
        import requests
        response = requests.post("https://textbelt.com/text", {
            "phone": to_number, "message": message, "key": "textbelt"
        })
        result = response.json()
        print(f"[TextBelt] {result}")
        return {"success": result.get("success", False)}
    except Exception as e:
        print(f"[TextBelt] Error: {e}")
        return {"success": False, "error": str(e)}


# ── UTILITIES ────────────────────────────────────────────────
def check_length(message: str) -> dict:
    length = len(message)
    return {
        "length": length,
        "fits_single_sms": length <= 160,
        "parts": (length // 160) + 1
    }


def validate_phone(phone: str) -> bool:
    phone = phone.strip()
    if not phone.startswith("+"):
        return False
    digits = phone[1:]
    if not digits.isdigit():
        return False
    return 10 <= len(phone) <= 16
