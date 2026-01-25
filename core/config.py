from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

if GOOGLE_CREDENTIALS:
    credentials_path = Path(GOOGLE_CREDENTIALS)
    if not credentials_path.is_absolute():
        project_root = Path(__file__).resolve().parents[1]
        GOOGLE_CREDENTIALS = str(project_root / credentials_path)
OCR_LOCAL_URL = os.getenv("OCR_LOCAL_URL")
