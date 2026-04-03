import os
from dotenv import load_dotenv

# Load environment variables from .env file (if local)
load_dotenv()

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
DATA_BUCKET = os.getenv("DATA_BUCKET")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SHIFT_HOURS = "shift-hours"
SHIFT_REPORT = "shift-report"
UNCATEGORIZED = "uncategorized"

def validate_config():
    missing = []
    if not GOOGLE_DRIVE_FOLDER_ID: missing.append("GOOGLE_DRIVE_FOLDER_ID")
    if not DATA_BUCKET: missing.append("DATA_BUCKET")
    if not SMTP_SERVER: missing.append("SMTP_SERVER")
    if not SENDER_EMAIL: missing.append("SENDER_EMAIL")
    if not RECEIVER_EMAIL: missing.append("RECEIVER_EMAIL")
    if not EMAIL_PASSWORD: missing.append("EMAIL_PASSWORD")
    if not SPREADSHEET_ID: missing.append("SPREADSHEET_ID")
    if not GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
