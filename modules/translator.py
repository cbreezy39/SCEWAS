# modules/translator.py
# ─────────────────────────────────────────────────────────────
# HYBRID TRANSLATION MODULE
#
# Design of a Low-Cost, Local-Language SMS Cybersecurity
# Early Warning and Public Awareness Infrastructure
#
# Translation Strategy (3 tiers):
#
#   Tier 1 — Pre-written human-verified translations
#             Most accurate. Used first always.
#
#   Tier 2 — NLLB-200 by Meta (Machine Translation)
#             facebook/nllb-200-distilled-600M
#             Selected specifically because it supports
#             Bemba (bem_Latn) and Nyanja (nya_Latn) —
#             low-resource languages not supported by
#             LibreTranslate or most other free MT tools.
#             Downloads ~2GB on first run, works offline after.
#
#   Tier 3 — Cybersecurity Glossary Fallback
#             Substitutes known cybersecurity terms into
#             the target language. Partial translation only.
#             Used when NLLB-200 is unavailable or fails.
#
#   Final  — English Default
#             If all tiers fail the message is sent in English.
#             The system never fails to deliver.
#
# Author  : Charmaine Isabel Lawrence  |  202201770
# ─────────────────────────────────────────────────────────────

# ── NLLB-200 LANGUAGE CODES ───────────────────────────────────
# NLLB-200 uses BCP-47 style codes with script identifiers
NLLB_LANG_CODES = {
    "bemba":   "bem_Latn",   # Bemba — Latin script
    "nyanja":  "nya_Latn",   # Nyanja — Latin script
    "english": "eng_Latn"    # English — Latin script
}

# ── MODEL CACHE ───────────────────────────────────────────────
# Model is loaded once per session and cached in memory.
# Loading takes ~30 seconds on first call, instant after that.
_nllb_model     = None
_nllb_tokenizer = None


def _load_nllb() -> bool:
    """
    Loads NLLB-200 distilled 600M model into memory.
    Returns True if successful, False if model unavailable.
    Downloads ~2GB on first run then works fully offline.
    """
    global _nllb_model, _nllb_tokenizer
    if _nllb_model is not None:
        return True  # Already loaded this session
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        model_name = "facebook/nllb-200-distilled-600M"
        print("[NLLB-200] Loading model — this may take 30 seconds on first run...")
        _nllb_tokenizer = AutoTokenizer.from_pretrained(model_name)
        _nllb_model     = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        print("[NLLB-200] Model loaded successfully.")
        return True
    except Exception as e:
        print(f"[NLLB-200] Could not load model: {e}")
        return False


def translate_with_nllb(text: str, target_language: str) -> str:
    """
    Translates English text to Bemba or Nyanja using NLLB-200.

    Parameters:
        text            : English source text
        target_language : "bemba" or "nyanja"

    Returns:
        Full translated sentence, or None if translation failed.

    Example:
        result = translate_with_nllb(
            "Never share your PIN with anyone.",
            "bemba"
        )
        # Returns: "Mutemwe ukufunda PIN yobe na umuntu uuli onse."
    """
    lang_code = NLLB_LANG_CODES.get(target_language.lower())
    if not lang_code:
        return None

    if not _load_nllb():
        return None

    try:
        inputs = _nllb_tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256
        )
        target_lang_id = _nllb_tokenizer.convert_tokens_to_ids(lang_code)
        translated = _nllb_model.generate(
            **inputs,
            forced_bos_token_id=target_lang_id,
            max_length=256
        )
        result = _nllb_tokenizer.decode(translated[0], skip_special_tokens=True)
        print(f"[NLLB-200] Translated to {target_language}: {result[:80]}...")
        return result
    except Exception as e:
        print(f"[NLLB-200] Translation error: {e}")
        return None


# ── CYBERSECURITY GLOSSARY ────────────────────────────────────
# Tier 3 fallback — partial translation via term substitution.
# Used ONLY when NLLB-200 is unavailable or fails.
# Key cybersecurity terms translated to Bemba and Nyanja.

GLOSSARY = {
    "scam":         {"bemba": "ubufyenyi",      "nyanja": "chinyengo"},
    "fraud":        {"bemba": "ubufyenyi",      "nyanja": "chinyengo"},
    "fraudster":    {"bemba": "ba kabolala",    "nyanja": "ma kwalala"},
    "warning":      {"bemba": "ICISHIBISHO",    "nyanja": "Chenjelesani"},
    "pin":          {"bemba": "PIN",            "nyanja": "PIN"},
    "password":     {"bemba": "password",       "nyanja": "password"},
    "money":        {"bemba": "indalama",       "nyanja": "ndalma"},
    "number":       {"bemba": "number",         "nyanja": "nambala"},
    "message":      {"bemba": "ubutumwa",       "nyanja": "uthenga"},
    "link":         {"bemba": "ilink",          "nyanja": "link"},
    "fake":         {"bemba": "ya bupuba",      "nyanja": "yabodza"},
    "never":        {"bemba": "mutemwe",        "nyanja": "osachita"},
    "immediately":  {"bemba": "bwangu",         "nyanja": "mwachangu"},
    "share":        {"bemba": "bampela",        "nyanja": "perekedza"},
    "network":      {"bemba": "network",        "nyanja": "netiweki"},
    "protect":      {"bemba": "sungeni",        "nyanja": "sungani"},
    "send money":   {"bemba": "tumila amafyashi",    "nyanja": "tuma ndalama"},
    "click":        {"bemba": "fwaya",          "nyanja": "gunda"},
    "stranger":     {"bemba": "umuntu ",       "nyanja": "muntu su uziba"},
    "share":        {"bemba": "bampela",        "nyanja": "gawana"},
}


def translate_with_glossary(text: str, language: str) -> str:
    """
    Partial translation via keyword substitution.
    Only used as Tier 3 fallback when NLLB-200 fails.
    """
    if language not in ("bemba", "nyanja"):
        return text
    result = text
    for eng, translations in GLOSSARY.items():
        local = translations.get(language, "")
        if local:
            result = result.replace(eng.upper(),      local.upper())
            result = result.replace(eng.capitalize(),  local.capitalize())
            result = result.replace(eng,               local)
    return result


# ── MAIN TRANSLATION FUNCTIONS ────────────────────────────────

def translate_tip(tip_dict: dict, language: str) -> str:
    """
    Translates an awareness tip using the hybrid 3-tier strategy.

    Tier 1 → Tier 2 (NLLB-200) → Tier 3 (Glossary) → English

    Parameters:
        tip_dict : dict with keys: english, bemba, nyanja
        language : "english", "bemba", or "nyanja"

    Returns:
        Translated tip text in the requested language.
    """
    lang = language.lower()

    # English — no translation needed
    if lang == "english":
        return tip_dict.get("english", "")

    # Tier 1: pre-written human-verified translation
    if lang == "bemba" and tip_dict.get("bemba"):
        return tip_dict["bemba"]
    if lang == "nyanja" and tip_dict.get("nyanja"):
        return tip_dict["nyanja"]

    # Tier 2: NLLB-200 machine translation
    print(f"[Translator] No pre-written {language} translation — calling NLLB-200...")
    result = translate_with_nllb(tip_dict["english"], lang)
    if result:
        return result

    # Tier 3: glossary fallback
    print(f"[Translator] NLLB-200 unavailable — using glossary fallback for {language}")
    glossary_result = translate_with_glossary(tip_dict["english"], lang)
    if glossary_result != tip_dict["english"]:
        return glossary_result

    # Final fallback: English
    print(f"[Translator] All tiers failed — defaulting to English")
    return tip_dict["english"]


def translate_alert(alert_row, language: str) -> str:
    """
    Translates an early warning alert using the hybrid 3-tier strategy.

    Tier 1 → Tier 2 (NLLB-200) → Tier 3 (Glossary) → English

    Parameters:
        alert_row : database row from the alerts table
        language  : "english", "bemba", or "nyanja"

    Returns:
        Translated alert text in the requested language.
    """
    lang = language.lower()

    # English — no translation needed
    if lang == "english":
        return alert_row["english"]

    # Tier 1: pre-written human-verified translation
    if lang == "bemba" and alert_row["bemba"]:
        return alert_row["bemba"]
    if lang == "nyanja" and alert_row["nyanja"]:
        return alert_row["nyanja"]

    # Tier 2: NLLB-200 machine translation
    print(f"[Translator] No pre-written {language} alert translation — calling NLLB-200...")
    result = translate_with_nllb(alert_row["english"], lang)
    if result:
        return result

    # Tier 3: glossary fallback
    print(f"[Translator] NLLB-200 unavailable — using glossary fallback for {language}")
    glossary_result = translate_with_glossary(alert_row["english"], lang)
    if glossary_result != alert_row["english"]:
        return glossary_result

    # Final fallback: English
    print(f"[Translator] All tiers failed — defaulting to English")
    return alert_row["english"]
