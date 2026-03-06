import os
from dotenv import load_dotenv

# Load environment variables from .env file (if local)
load_dotenv()

# Google Cloud Config
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
DATA_BUCKET = os.getenv("DATA_BUCKET")

# SMTP Config
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Constants
SHIFT_HOURS = "shift-hours"
SHIFT_REPORT = "shift-report"
UNCATEGORIZED = "uncategorized"

# Validation
def validate_config():
    missing = []
    if not GOOGLE_DRIVE_FOLDER_ID: missing.append("GOOGLE_DRIVE_FOLDER_ID")
    if not DATA_BUCKET: missing.append("DATA_BUCKET")
    if not SMTP_SERVER: missing.append("SMTP_SERVER")
    if not SENDER_EMAIL: missing.append("SENDER_EMAIL")
    if not RECEIVER_EMAIL: missing.append("RECEIVER_EMAIL")
    if not EMAIL_PASSWORD: missing.append("EMAIL_PASSWORD")
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
