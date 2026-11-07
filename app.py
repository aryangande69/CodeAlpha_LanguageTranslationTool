"""
Lingua AI — Language Translator
CodeAlpha AI Internship — Task 1

Features: 18 languages, auto-detect, swap, voice typing, copy, listen,
download, session history and a Google -> MyMemory fallback.
"""

import html
import io
import json
import time
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components
from deep_translator import GoogleTranslator, MyMemoryTranslator

try:
    from langdetect import DetectorFactory, detect

    DetectorFactory.seed = 0  # makes detection results repeatable
except ImportError:
    detect = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


# ----------------------------------------------------------------------------
# 1. Page setup (must be the first Streamlit call)
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Lingua AI | Language Translator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_CHARS = 5000
MYMEMORY_MAX_CHARS = 500   # the backup service only accepts short text
HISTORY_LIMIT = 30
AUTO = "Auto detect"

PHRASES = {
    "👋 Greeting": "Hello! How are you today?",
    "🙏 Thank you": "Thank you so much for your help.",
    "📍 Directions": "Where is the nearest railway station?",
    "🏥 Emergency": "I need help. Please call a doctor.",
    "🍽 Restaurant": "Could I see the menu, please?",
}

# code = Google code, mm = MyMemory code, speech = voice locale
LANGUAGES = {
    "Arabic":     {"code": "ar",    "mm": "ar-SA", "speech": "ar-SA", "native": "العربية",   "rtl": True},
    "Bengali":    {"code": "bn",    "mm": "bn-IN", "speech": "bn-IN", "native": "বাংলা",      "rtl": False},
    "Chinese":    {"code": "zh-CN", "mm": "zh-CN", "speech": "zh-CN", "native": "中文",        "rtl": False},
    "English":    {"code": "en",    "mm": "en-GB", "speech": "en-IN", "native": "English",    "rtl": False},
    "French":     {"code": "fr",    "mm": "fr-FR", "speech": "fr-FR", "native": "Français",   "rtl": False},
    "German":     {"code": "de",    "mm": "de-DE", "speech": "de-DE", "native": "Deutsch",    "rtl": False},
    "Gujarati":   {"code": "gu",    "mm": "gu-IN", "speech": "gu-IN", "native": "ગુજરાતી",    "rtl": False},
    "Hindi":      {"code": "hi",    "mm": "hi-IN", "speech": "hi-IN", "native": "हिन्दी",      "rtl": False},
    "Japanese":   {"code": "ja",    "mm": "ja-JP", "speech": "ja-JP", "native": "日本語",      "rtl": False},
    "Kannada":    {"code": "kn",    "mm": "kn-IN", "speech": "kn-IN", "native": "ಕನ್ನಡ",      "rtl": False},
    "Korean":     {"code": "ko",    "mm": "ko-KR", "speech": "ko-KR", "native": "한국어",      "rtl": False},
    "Marathi":    {"code": "mr",    "mm": "mr-IN", "speech": "mr-IN", "native": "मराठी",      "rtl": False},
    "Portuguese": {"code": "pt",    "mm": "pt-PT", "speech": "pt-PT", "native": "Português",  "rtl": False},
    "Russian":    {"code": "ru",    "mm": "ru-RU", "speech": "ru-RU", "native": "Русский",    "rtl": False},
    "Spanish":    {"code": "es",    "mm": "es-ES", "speech": "es-ES", "native": "Español",    "rtl": False},
    "Tamil":      {"code": "ta",    "mm": "ta-IN", "speech": "ta-IN", "native": "தமிழ்",      "rtl": False},
    "Telugu":     {"code": "te",    "mm": "te-IN", "speech": "te-IN", "native": "తెలుగు",     "rtl": False},
    "Urdu":       {"code": "ur",    "mm": "ur-PK", "speech": "ur-PK", "native": "اردو",       "rtl": True},
}
SOURCE_OPTIONS = [AUTO] + list(LANGUAGES)
TARGET_OPTIONS = list(LANGUAGES)


def lang_label(name: str) -> str:
    """Text shown in the dropdowns, e.g. 'Marathi · मराठी'."""
    if name == AUTO:
        return "✨ Auto detect"
    return f"{name} · {LANGUAGES[name]['native']}"


# ----------------------------------------------------------------------------
# 2. HTML helper + styling
# ----------------------------------------------------------------------------
def ui(markup: str) -> None:
    """Render HTML.

    Streamlit's markdown treats indented lines and blank lines inside HTML as
    a *code block* (that was the "distorted text" bug). Flattening the markup
    first (no indentation, no blank lines) makes it render as real HTML.
    """
    flat = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
:root { --ink:#26324b; --muted:#73809a; --line:rgba(255,255,255,.72); --brand:#6558d9; --teal:#20b8ae; }
html, body, [class*="css"] { font-family:'DM Sans','Segoe UI',sans-serif; }
header[data-testid="stHeader"] { background:transparent; }
.stApp {
 color:var(--ink);
 background-color:#eaf1ff;
 background-image:
  radial-gradient(ellipse at 12% 12%, rgba(166,151,255,.68) 0, transparent 34%),
  radial-gradient(ellipse at 88% 16%, rgba(119,224,218,.58) 0, transparent 32%),
  radial-gradient(ellipse at 50% 92%, rgba(255,190,219,.48) 0, transparent 38%),
  linear-gradient(135deg,#edf1ff 0%,#f5f4ff 48%,#e8f8f7 100%);
 background-attachment:fixed;
}
.block-container { max-width:1200px; padding-top:1.25rem; padding-bottom:3rem; }
/* Main glass header */
.topbar {
 display:flex; flex-wrap:wrap; gap:12px; justify-content:space-between; align-items:center;
 padding:16px 22px; border-radius:22px;
 background:rgba(255,255,255,.38); border:1px solid rgba(255,255,255,.82);
 box-shadow:0 12px 38px rgba(87,101,151,.10), inset 0 1px 0 rgba(255,255,255,.9);
 backdrop-filter:blur(28px) saturate(180%); -webkit-backdrop-filter:blur(28px) saturate(180%);
}
.brand { font-size:1.32rem; font-weight:800; color:#393b78; letter-spacing:-.5px; }
.brand-icon { display:inline-block; background:linear-gradient(135deg,#8075ed,#54c9c1); color:#fff; padding:8px 10px; border-radius:13px; margin-right:9px; box-shadow:0 5px 15px rgba(104,112,220,.22); }
.pills { display:flex; gap:8px; flex-wrap:wrap; }
.pill { font-size:12px; font-weight:700; color:#5953a6; background:rgba(255,255,255,.48); border:1px solid rgba(255,255,255,.78); border-radius:999px; padding:6px 12px; }
.hero { text-align:center; padding:43px 8px 28px; }
.hero h1 { font-size:clamp(2.25rem,5vw,3.65rem); font-weight:800; letter-spacing:-2px; margin:0; padding:0; background:linear-gradient(100deg,#5146bd 5%,#8b69d8 52%,#159f9c 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hero p { color:#707c98; font-size:1.08rem; margin:.55rem 0 0; }
/* Every Streamlit bordered container becomes a translucent glass pane */
div[data-testid="stVerticalBlockBorderWrapper"] {
 background:rgba(255,255,255,.34) !important;
 border:1px solid rgba(255,255,255,.82) !important;
 border-radius:24px !important;
 box-shadow:0 16px 42px rgba(75,91,145,.10), inset 0 1px 0 rgba(255,255,255,.82) !important;
 backdrop-filter:blur(26px) saturate(175%); -webkit-backdrop-filter:blur(26px) saturate(175%);
}
.panel-title { font-size:1.16rem; font-weight:800; color:#303b5b; letter-spacing:-.25px; }
.panel-sub { font-size:.88rem; color:#7b86a0; margin:3px 0 12px; }
/* Text input: milky translucent glass, not a solid grey box */
div[data-testid="stTextArea"] textarea {
 border-radius:17px !important; background:rgba(255,255,255,.48) !important;
 border:1px solid rgba(255,255,255,.9) !important; color:#29344f !important;
 font-size:1.04rem !important; line-height:1.6 !important;
 box-shadow:inset 0 2px 10px rgba(105,117,160,.045),0 5px 18px rgba(91,105,153,.045) !important;
 backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px);
}
div[data-testid="stTextArea"] textarea:focus { border-color:rgba(125,111,224,.65) !important; box-shadow:0 0 0 3px rgba(126,111,224,.12) !important; }
div[data-testid="stTextArea"] label { color:#64718e !important; }
.result-box, .placeholder {
 min-height:245px; padding:18px 20px; border-radius:17px;
 background:rgba(255,255,255,.43); border:1px solid rgba(255,255,255,.86);
 box-shadow:inset 0 1px 0 rgba(255,255,255,.9),0 6px 22px rgba(91,105,153,.05);
 backdrop-filter:blur(18px) saturate(160%); -webkit-backdrop-filter:blur(18px) saturate(160%);
 font-size:1.08rem; line-height:1.7; word-break:break-word; color:#29344f;
}
.placeholder { display:flex; align-items:center; justify-content:center; text-align:center; color:#929db4; border-style:dashed; }
.meta { display:flex; justify-content:space-between; align-items:center; gap:8px; color:#7d89a2; font-size:.82rem; margin:9px 0 5px; }
.badge { background:rgba(130,116,225,.12); color:#6558bb; border:1px solid rgba(130,116,225,.16); border-radius:999px; padding:4px 11px; font-weight:700; font-size:.78rem; }
.badge-teal { background:rgba(34,184,171,.12); color:#16877f; border-color:rgba(34,184,171,.18); }
/* Native controls should look like floating glass chips */
.stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {
 background:rgba(255,255,255,.48) !important; border:1px solid rgba(255,255,255,.88) !important;
 border-radius:14px !important; box-shadow:0 5px 16px rgba(83,99,148,.05) !important;
 backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
}
div.stButton > button, div.stDownloadButton > button {
 width:100%; border-radius:14px; min-height:2.85rem; font-weight:700;
 background:rgba(255,255,255,.48); color:#56558e; border:1px solid rgba(255,255,255,.9);
 box-shadow:0 6px 18px rgba(83,99,148,.07),inset 0 1px 0 rgba(255,255,255,.9);
 transition:transform .18s ease,box-shadow .18s ease,background .18s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover { transform:translateY(-2px); background:rgba(255,255,255,.72); border-color:rgba(139,126,226,.55); box-shadow:0 10px 24px rgba(83,99,148,.12); color:#49448f; }
div.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
 background:linear-gradient(105deg,#7569df,#9a79df 52%,#43bdb4) !important; border:1px solid rgba(255,255,255,.65) !important; color:#fff !important;
 min-height:3.25rem; font-size:1.06rem; box-shadow:0 10px 25px rgba(111,99,205,.25),inset 0 1px 0 rgba(255,255,255,.35) !important;
}
button:focus-visible, textarea:focus-visible { outline:3px solid rgba(127,112,226,.55) !important; outline-offset:2px; }
.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:8px 0 18px; }
.stat { background:rgba(255,255,255,.38); border:1px solid rgba(255,255,255,.82); border-radius:19px; padding:14px 17px; box-shadow:0 10px 28px rgba(75,91,145,.08),inset 0 1px 0 rgba(255,255,255,.9); backdrop-filter:blur(22px); -webkit-backdrop-filter:blur(22px); }
.stat b { display:block; font-size:1.55rem; font-weight:800; color:#51499e; }
.stat span { color:#7b86a0; font-size:.82rem; }
button[data-baseweb="tab"] { font-weight:700; font-size:1rem; color:#747e99; }
button[data-baseweb="tab"][aria-selected="true"] { color:#5c54b5; }
div[data-testid="stPopover"] button { width:100%; border-radius:12px; min-height:2.8rem; font-weight:700; }
div[data-testid="stExpander"] { background:rgba(255,255,255,.30); border:1px solid rgba(255,255,255,.72); border-radius:16px; backdrop-filter:blur(18px); }
.footer { text-align:center; color:#8792aa; padding-top:26px; font-size:.85rem; }
@media (max-width:700px) { .block-container { padding-left:.8rem; padding-right:.8rem; } .topbar .pills { display:none; } .hero { padding-top:30px; } }
@media (prefers-reduced-transparency: reduce) { div[data-testid="stVerticalBlockBorderWrapper"],.topbar,.stat { backdrop-filter:none; background:rgba(255,255,255,.88); } }
</style>
"""

HEADER = """
<div class="topbar">
    <div class="brand"><span class="brand-icon">🌐</span>Lingua AI</div>
    <div class="pills">
        <span class="pill">18 languages</span>
        <span class="pill">Auto-detect</span>
        <span class="pill">Voice typing</span>
        <span class="pill">Listen</span>
    </div>
</div>
<div class="hero">
    <h1>Words connect worlds.</h1>
    <p>Translate, speak and understand languages effortlessly.</p>
</div>
"""

ABOUT_TEXT = """
Lingua AI is a student-built language translator made with Python and Streamlit
for the CodeAlpha AI Internship (Task 1).

**Features:** automatic language detection, 18 languages, voice typing,
text-to-speech, copy and download, and a session history.

**How it works:** your text is sent to Google Translate. If that service is busy,
the app tries MyMemory (short texts only). Both are free services, so they can
limit requests and are not guaranteed to be available.

**Privacy:** text goes to external translation providers, and voice typing sends
audio to Google's speech recognition. Please do not submit confidential, legal
or medical information.
"""

ACTION_BAR = """
<style>
body { margin:0; font-family:'Segoe UI',system-ui,sans-serif; }
.row { display:flex; gap:8px; }
button { background:#fff; border:1px solid #d9dcf0; border-radius:10px; padding:9px 16px;
         cursor:pointer; font-weight:600; font-size:14px; color:#4540b5; }
button:hover { background:#f3f2ff; }
button:focus-visible { outline:3px solid #8b86ff; outline-offset:2px; }
</style>
<div class="row">
    <button id="copy" type="button">📋 Copy</button>
    <button id="listen" type="button">🔊 Listen</button>
</div>
<script>
const text = __TEXT__;
const lang = __LANG__;
const copyBtn = document.getElementById("copy");
const listenBtn = document.getElementById("listen");

function flash(btn, message, original) {
    btn.innerText = message;
    setTimeout(() => { btn.innerText = original; }, 1600);
}
function fallbackCopy() {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(area);
    return ok;
}
copyBtn.onclick = async () => {
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; }
    catch (e) { ok = fallbackCopy(); }
    flash(copyBtn, ok ? "✅ Copied!" : "Copy failed", "📋 Copy");
};
listenBtn.onclick = () => {
    if (!window.speechSynthesis) { flash(listenBtn, "Not supported", "🔊 Listen"); return; }
    window.speechSynthesis.cancel();
    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = lang;
    speech.onend = () => { listenBtn.innerText = "🔊 Listen"; };
    speech.onerror = () => { flash(listenBtn, "Try again", "🔊 Listen"); };
    listenBtn.innerText = "⏹ Playing…";
    window.speechSynthesis.speak(speech);
};
</script>
"""


def action_bar(text: str, locale: str) -> None:
    """Copy + Listen buttons (they need the browser, so they use a small HTML component)."""
    safe_text = json.dumps(text).replace("<", "\\u003c")
    page = ACTION_BAR.replace("__TEXT__", safe_text).replace("__LANG__", json.dumps(locale))
    components.html(page, height=52)


# ----------------------------------------------------------------------------
# 3. Session state and button callbacks
# ----------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "source_lang": AUTO,
        "target_lang": "Marathi",
        "input_text": "",
        "result": "",
        "result_target": "",
        "result_source": "",
        "total_translations": 0,
        "total_chars": 0,
        "languages_used": set(),
        "provider": "",
        "translation_time": "",
        "last_request": 0.0,
        "history": [],
        "pending_voice_text": None,
        "voice_error": None,
        "notice": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


GOOGLE_DETECT_URL = "https://translate.googleapis.com/translate_a/single"
URDU_LETTERS = set("ٹڈڑںےگچپژھہ")


def script_of(text: str) -> str | None:
    """Find the main writing system of the text from its Unicode characters (works offline)."""
    ranges = {
        "Gujarati": (0x0A80, 0x0AFF), "Bengali": (0x0980, 0x09FF), "Tamil": (0x0B80, 0x0BFF),
        "Telugu": (0x0C00, 0x0C7F), "Kannada": (0x0C80, 0x0CFF), "Korean": (0xAC00, 0xD7AF),
        "Russian": (0x0400, 0x04FF), "kana": (0x3040, 0x30FF), "han": (0x4E00, 0x9FFF),
        "devanagari": (0x0900, 0x097F), "arabic": (0x0600, 0x06FF),
    }
    counts: dict[str, int] = {}
    for ch in text:
        code = ord(ch)
        for name, (low, high) in ranges.items():
            if low <= code <= high:
                counts[name] = counts.get(name, 0) + 1
                break
        else:
            if ch.isalpha() and code < 0x0250:
                counts["latin"] = counts.get("latin", 0) + 1
    if not counts:
        return None
    if "kana" in counts:
        return "Japanese"
    if "han" in counts and len(counts) == 1:
        return "Chinese"
    top = max(counts, key=counts.get)
    return "Chinese" if top == "han" else top


def code_to_name(code: str) -> str | None:
    code = code.lower()
    for name, info in LANGUAGES.items():
        google_code = info["code"].lower()
        if google_code == code or google_code.split("-")[0] == code.split("-")[0]:
            return name
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def google_detect_code(text: str) -> str:
    """Ask Google which language this is (accurate, also for Hindi vs Marathi)."""
    response = requests.get(
        GOOGLE_DETECT_URL,
        params={"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text},
        timeout=4,
    )
    response.raise_for_status()
    code = response.json()[2]
    if not isinstance(code, str):
        raise ValueError("No language returned")
    return code  # errors are raised, so they are never cached


def detect_language_name(text: str) -> str | None:
    """Detect the language of `text`; return one of our language names or None.

    Order: 1) writing system (instant, offline)  2) Google  3) langdetect  4) safe defaults.
    """
    text = text.strip()
    if len(text) < 2:
        return None
    script = script_of(text)
    if script is None:
        return None
    if script in LANGUAGES:          # Gujarati, Tamil, Japanese, ... are certain from the script
        return script

    try:
        name = code_to_name(google_detect_code(text[:300]))
        if name:
            return name
    except Exception:
        pass

    if detect is not None:
        try:
            name = code_to_name(detect(text))
            if name:
                return name
        except Exception:
            pass

    if script == "arabic":
        return "Urdu" if any(ch in URDU_LETTERS for ch in text) else "Arabic"
    if script == "devanagari":
        return "Hindi"
    if script == "latin" and text.isascii():
        return "English"
    return None


def clear_all() -> None:
    ss = st.session_state
    ss.input_text = ""
    ss.result = ""
    ss.provider = ""
    ss.voice_error = None


def set_phrase(phrase: str) -> None:
    ss = st.session_state
    ss.input_text = phrase
    ss.source_lang = AUTO
    ss.result = ""
    ss.provider = ""


def swap_languages() -> None:
    ss = st.session_state
    source = ss.source_lang
    if source == AUTO:  # try to use the detected language instead
        source = detect_language_name(ss.input_text)
        if not source:
            ss.notice = ("warning", "Choose a source language (or type a longer text so it can be detected) before swapping.")
            return
    if source == ss.target_lang:
        return
    ss.source_lang, ss.target_lang = ss.target_lang, source
    if ss.result:  # the translation becomes the new input
        ss.input_text = ss.result
    ss.result = ""
    ss.provider = ""


def clear_history() -> None:
    st.session_state.history = []


def restore_history(index: int) -> None:
    ss = st.session_state
    item = ss.history[index]
    ss.input_text = item["original"]
    if item["source"] in LANGUAGES:
        ss.source_lang = item["source"]
    if item["target"] in LANGUAGES:
        ss.target_lang = item["target"]
    ss.result = ""
    ss.provider = ""


def save_history(source: str, target: str, original: str, translated: str, provider: str) -> None:
    entry = {
        "time": datetime.now().strftime("%d %b, %H:%M"),
        "source": source,
        "target": target,
        "original": original,
        "translated": translated,
        "provider": provider,
    }
    st.session_state.history.insert(0, entry)
    del st.session_state.history[HISTORY_LIMIT:]


# ----------------------------------------------------------------------------
# 4. Translation engine (Google first, MyMemory as backup)
# ----------------------------------------------------------------------------
class TranslationError(Exception):
    """A friendly message for the user plus technical details for debugging."""

    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.message = message
        self.details = details


def is_network_error(error: Exception) -> bool:
    return isinstance(error, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))


def translate_text(text: str, source: str, target: str) -> tuple[str, str]:
    """Return (translated_text, provider_name) or raise TranslationError."""
    text = text.strip()
    source_code = "auto" if source == AUTO else LANGUAGES[source]["code"]
    target_code = LANGUAGES[target]["code"]
    network_down = False

    # Provider 1: Google Translate
    try:
        translated = GoogleTranslator(source=source_code, target=target_code).translate(text)
        if translated and translated.strip():
            return translated, "Google Translate"
        google_error = "Google returned an empty response."
    except Exception as error:  # noqa: BLE001
        google_error = f"{type(error).__name__}: {error}"
        network_down = is_network_error(error)

    # Provider 2: MyMemory (needs a known source language and short text)
    fallback_source = detect_language_name(text) if source == AUTO else source
    if not fallback_source:
        raise TranslationError(
            "Google Translate did not respond and the source language could not be detected. "
            "Please choose the source language manually and try again.",
            google_error,
        )
    if len(text) > MYMEMORY_MAX_CHARS:
        message = (
            "The translation service is not reachable. Check your internet connection and try again."
            if network_down
            else "The main service is busy and the backup accepts only 500 characters. "
            "Wait a minute or try a shorter text."
        )
        raise TranslationError(message, google_error)

    try:
        translated = MyMemoryTranslator(
            source=LANGUAGES[fallback_source]["mm"],
            target=LANGUAGES[target]["mm"],
        ).translate(text)
        if translated and translated.strip() and "MYMEMORY WARNING" not in translated:
            return translated, "MyMemory"
        backup_error = "MyMemory returned no usable translation (its free quota may be used up)."
    except Exception as error:  # noqa: BLE001
        backup_error = f"{type(error).__name__}: {error}"
        network_down = network_down and is_network_error(error)

    message = (
        "Could not reach the translation services. Check your internet connection and try again."
        if network_down
        else "Both free translation services failed. Please wait a moment and try again."
    )
    raise TranslationError(message, f"Google: {google_error}\nMyMemory: {backup_error}")


# ----------------------------------------------------------------------------
# 5. Voice typing
# ----------------------------------------------------------------------------
def voice_callback() -> None:
    ss = st.session_state
    audio = ss.get("voice_recording")
    if audio is None:
        ss.voice_error = "Record your voice first, then press 'Convert speech to text'."
        return
    if ss.source_lang == AUTO:
        ss.voice_error = "Choose the language you are speaking in the 'From' box first."
        return
    if sr is None:
        ss.voice_error = "Voice typing needs a package. Run: pip install SpeechRecognition"
        return
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio.getvalue())) as source:
            data = recognizer.record(source)
        ss.pending_voice_text = recognizer.recognize_google(
            data, language=LANGUAGES[ss.source_lang]["speech"]
        )
        ss.voice_error = None
    except sr.UnknownValueError:
        ss.voice_error = "Could not understand the audio. Speak clearly and try again."
    except sr.RequestError:
        ss.voice_error = "The speech service could not be reached. Check your internet connection."
    except Exception as error:  # noqa: BLE001
        ss.voice_error = f"Voice typing failed: {error}"


# ----------------------------------------------------------------------------
# 6. Output panel
# ----------------------------------------------------------------------------
def render_output(slot) -> None:
    ss = st.session_state
    with slot.container():
        if not ss.result:
            ui('<div class="placeholder">✨ Your translation will appear here.</div>')
            return

        info = LANGUAGES.get(ss.result_target, LANGUAGES["English"])
        direction = "rtl" if info["rtl"] else "ltr"
        # Escape the text so it can never be treated as HTML; <br> keeps line breaks.
        safe = html.escape(ss.result).replace("$", "&#36;").replace("\n", "<br>")
        ui(f'<div class="result-box" dir="{direction}">{safe}</div>')
        ui(
            f'<div class="meta"><span class="badge">{html.escape(ss.result_source or "Auto")} → '
            f'{html.escape(ss.result_target)}</span>'
            f"<span>{html.escape(ss.provider)} · {ss.translation_time}</span></div>"
        )
        action_bar(ss.result, info["speech"])
        st.download_button(
            "⬇ Download as .txt",
            data=ss.result,
            file_name="lingua_translation.txt",
            mime="text/plain",
            key="download_btn",
        )


# ----------------------------------------------------------------------------
# 7. Page
# ----------------------------------------------------------------------------
def render_stats(slot) -> None:
    s = st.session_state
    with slot.container():
        ui(
            f"""
            <div class="stats">
                <div class="stat"><b>{s.total_translations}</b><span>Translations this session</span></div>
                <div class="stat"><b>{s.total_chars:,}</b><span>Characters translated</span></div>
                <div class="stat"><b>{len(s.languages_used)}</b><span>Languages used</span></div>
            </div>
            """
        )


init_state()
ss = st.session_state

# Voice text must be applied BEFORE the text box is created.
if ss.pending_voice_text is not None:
    ss.input_text = ss.pending_voice_text
    ss.pending_voice_text = None

ui(CSS)
ui(HEADER)
stats_slot = st.empty()  # filled at the end so the numbers are always up to date

tab_translate, tab_history, tab_about = st.tabs(["🌐 Translate", "📚 History", "ℹ️ About"])

with tab_translate:
    # Language bar: From | swap | To
    with st.container(border=True):
        col_from, col_swap, col_to = st.columns([5, 1.6, 5], vertical_alignment="bottom")
        col_from.selectbox("From", SOURCE_OPTIONS, key="source_lang", format_func=lang_label)
        col_swap.button("⇄ Swap", key="swap_btn", on_click=swap_languages, help="Swap the two languages")
        col_to.selectbox("To", TARGET_OPTIONS, key="target_lang", format_func=lang_label)

    if ss.notice:
        getattr(st, ss.notice[0])(ss.notice[1])
        ss.notice = None

    left, right = st.columns(2, gap="large")

    with left:
        with st.container(border=True):
            ui(
                """
                <div class="panel-title">✍️ Your text</div>
                <div class="panel-sub">Type, paste or speak. Press Ctrl+Enter or click outside the box to detect the language.</div>
                """
            )
            st.text_area(
                "Text to translate",
                key="input_text",
                height=245,
                max_chars=MAX_CHARS,
                placeholder="Type or paste your text here…",
                label_visibility="collapsed",
            )
            current_text = ss.input_text
            detected_now = (
                detect_language_name(current_text)
                if ss.source_lang == AUTO and current_text.strip()
                else None
            )
            pill = (
                f'<span class="badge badge-teal">🔍 Detected: {html.escape(detected_now)}</span>'
                if detected_now
                else '<span class="badge">🔍 Language: auto-detect</span>'
                if ss.source_lang == AUTO
                else "<span></span>"
            )
            ui(f'<div class="meta">{pill}<span>{len(current_text):,} / {MAX_CHARS:,}</span></div>')

            btn_clear, btn_phrase = st.columns(2)
            btn_clear.button("Clear", key="clear_btn", on_click=clear_all)
            with btn_phrase.popover("💬 Quick phrases"):
                for number, (label, phrase) in enumerate(PHRASES.items()):
                    st.button(label, key=f"phrase_{number}", on_click=set_phrase, args=(phrase,))

            with st.expander("🎙 Voice typing"):
                st.caption("Choose the language you speak in 'From', record, then convert.")
                st.audio_input("Record your voice", key="voice_recording")
                st.button("Convert speech to text", key="voice_convert", on_click=voice_callback)
                if ss.voice_error:
                    st.error(ss.voice_error)

    with right:
        with st.container(border=True):
            ui(
                """
                <div class="panel-title">✨ Translation</div>
                <div class="panel-sub">Your result appears here, ready to copy, hear or download.</div>
                """
            )
            output_slot = st.empty()  # filled after the Translate logic runs

    translate_clicked = st.button("Translate →", type="primary", key="translate_btn")

    if translate_clicked:
        text = ss.input_text.strip()
        source, target = ss.source_lang, ss.target_lang

        if not text:
            st.warning("Please enter some text first.")
        elif len(text) > MAX_CHARS:
            st.warning(f"Maximum {MAX_CHARS:,} characters allowed.")
        elif source == target:
            st.warning("Source and target languages are the same. Please choose different languages.")
        elif time.time() - ss.last_request < 2:
            st.warning("Please wait a moment before translating again.")
        else:
            ss.last_request = time.time()
            ss.result = ""  # never show an old result for new input
            ss.provider = ""
            detected = detect_language_name(text) if source == AUTO else source
            try:
                with st.spinner("Translating your text…"):
                    translated, provider = translate_text(text, source, target)
            except TranslationError as error:
                st.error(error.message)
                if error.details:
                    with st.expander("Technical details"):
                        st.code(error.details, language=None)
            else:
                ss.result = translated
                ss.result_target = target
                ss.result_source = detected or "Auto"
                ss.provider = provider
                ss.translation_time = datetime.now().strftime("%H:%M")
                ss.total_translations += 1
                ss.total_chars += len(text)
                ss.languages_used.add(target)
                save_history(detected or "Auto detected", target, text, translated, provider)
                if source == AUTO and detected == target:
                    st.caption(f"Note: the text looks like it is already in {target}.")

    render_output(output_slot)

with tab_history:
    if not ss.history:
        st.info("No translations yet. Your recent translations will be listed here.")
    else:
        st.button("Clear history", key="clear_history_btn", on_click=clear_history)
        for index, item in enumerate(ss.history):
            with st.container(border=True):
                ui(
                    f'<div class="meta"><span class="badge">{html.escape(item["source"])} → '
                    f'{html.escape(item["target"])}</span><span>{item["time"]} · '
                    f'{html.escape(item["provider"])}</span></div>'
                )
                st.caption("Original")
                st.text(item["original"])
                st.caption("Translation")
                st.text(item["translated"])
                st.button(
                    "↩ Reuse this text",
                    key=f"history_{index}",
                    on_click=restore_history,
                    args=(index,),
                )

with tab_about:
    st.markdown(ABOUT_TEXT)

render_stats(stats_slot)
ui('<div class="footer">🌐 Lingua AI · CodeAlpha AI Internship — Task 1 · Made with Python and Streamlit</div>')
