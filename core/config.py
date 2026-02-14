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
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_LANGUAGE = os.getenv("TMDB_LANGUAGE", "ru-RU")
TMDB_REGION = os.getenv("TMDB_REGION", "RU")
try:
    TMDB_TIMEOUT_SECONDS = float(os.getenv("TMDB_TIMEOUT_SECONDS", "12"))
except ValueError:
    TMDB_TIMEOUT_SECONDS = 12.0
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
OMDB_BASE_URL = os.getenv("OMDB_BASE_URL", "https://www.omdbapi.com/")
try:
    OMDB_TIMEOUT_SECONDS = float(os.getenv("OMDB_TIMEOUT_SECONDS", "8"))
except ValueError:
    OMDB_TIMEOUT_SECONDS = 8.0
KINOPOISK_TOKEN = os.getenv("KINOPOISK_TOKEN")

if GOOGLE_CREDENTIALS:
    credentials_path = Path(GOOGLE_CREDENTIALS)
    if not credentials_path.is_absolute():
        project_root = Path(__file__).resolve().parents[1]
        GOOGLE_CREDENTIALS = str(project_root / credentials_path)
