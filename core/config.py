from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
STARTUP_CHECK_SHEET = os.getenv("STARTUP_CHECK_SHEET", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
_gemini_fallback_raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash")
GEMINI_FALLBACK_MODELS = [
    value.strip()
    for value in _gemini_fallback_raw.split(",")
    if value.strip()
]
try:
    GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
except ValueError:
    GEMINI_MAX_RETRIES = 3
try:
    GEMINI_RETRY_BASE_DELAY_SECONDS = float(
        os.getenv("GEMINI_RETRY_BASE_DELAY_SECONDS", "1.5")
    )
except ValueError:
    GEMINI_RETRY_BASE_DELAY_SECONDS = 1.5
try:
    GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))
except ValueError:
    GEMINI_TIMEOUT_SECONDS = 20.0
try:
    GEMINI_TOTAL_TIMEOUT_SECONDS = float(
        os.getenv("GEMINI_TOTAL_TIMEOUT_SECONDS", "60")
    )
except ValueError:
    GEMINI_TOTAL_TIMEOUT_SECONDS = 60.0
MISTRAL_API_KEY = os.getenv("MISTRALAPI") or os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_AUDIO_MODEL = os.getenv("MISTRAL_AUDIO_MODEL", "voxtral-mini-latest")
try:
    MISTRAL_TIMEOUT_SECONDS = float(os.getenv("MISTRAL_TIMEOUT_SECONDS", "30"))
except ValueError:
    MISTRAL_TIMEOUT_SECONDS = 30.0
try:
    MISTRAL_MAX_RETRIES = int(os.getenv("MISTRAL_MAX_RETRIES", "2"))
except ValueError:
    MISTRAL_MAX_RETRIES = 2
try:
    MISTRAL_RETRY_BASE_DELAY_SECONDS = float(
        os.getenv("MISTRAL_RETRY_BASE_DELAY_SECONDS", "1.2")
    )
except ValueError:
    MISTRAL_RETRY_BASE_DELAY_SECONDS = 1.2
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_LANGUAGE = os.getenv("TMDB_LANGUAGE", "ru-RU")
TMDB_REGION = os.getenv("TMDB_REGION", "RU")
try:
    TMDB_TIMEOUT_SECONDS = float(os.getenv("TMDB_TIMEOUT_SECONDS", "12"))
except ValueError:
    TMDB_TIMEOUT_SECONDS = 12.0
KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY") or os.getenv("KP_API_KEY")
KINOPOISK_BASE_URL = os.getenv("KINOPOISK_BASE_URL", "https://api.kinopoisk.dev/v1.4")
try:
    KINOPOISK_TIMEOUT_SECONDS = float(os.getenv("KINOPOISK_TIMEOUT_SECONDS", "10"))
except ValueError:
    KINOPOISK_TIMEOUT_SECONDS = 10.0
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
OMDB_BASE_URL = os.getenv("OMDB_BASE_URL", "https://www.omdbapi.com/")
try:
    OMDB_TIMEOUT_SECONDS = float(os.getenv("OMDB_TIMEOUT_SECONDS", "8"))
except ValueError:
    OMDB_TIMEOUT_SECONDS = 8.0
try:
    EXTERNAL_API_MAX_RETRIES = int(os.getenv("EXTERNAL_API_MAX_RETRIES", "3"))
except ValueError:
    EXTERNAL_API_MAX_RETRIES = 3
try:
    EXTERNAL_API_RETRY_BASE_DELAY_SECONDS = float(
        os.getenv("EXTERNAL_API_RETRY_BASE_DELAY_SECONDS", "1.1")
    )
except ValueError:
    EXTERNAL_API_RETRY_BASE_DELAY_SECONDS = 1.1
try:
    SHEETS_THREAD_TIMEOUT_SECONDS = float(os.getenv("SHEETS_THREAD_TIMEOUT_SECONDS", "15"))
except ValueError:
    SHEETS_THREAD_TIMEOUT_SECONDS = 15.0

if GOOGLE_CREDENTIALS:
    credentials_path = Path(GOOGLE_CREDENTIALS)
    if not credentials_path.is_absolute():
        project_root = Path(__file__).resolve().parents[1]
        GOOGLE_CREDENTIALS = str(project_root / credentials_path)
