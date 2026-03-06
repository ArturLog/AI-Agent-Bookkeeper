import os
import io
import google.auth
import smtplib
import datetime
import functions_framework
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import storage
from google.cloud import vision
from dateutil.relativedelta import relativedelta


SHIFT_HOURS = "shift-hours"
SHIFT_REPORT = "shift-report"

def get_drive_service():
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=credentials)

def categorize_image(vision_client, content):
    """
    Categorizes the image based on detected text.
    """
    image = vision.Image(content=content)
    response = vision_client.document_text_detection(image=image)
    text = response.full_text_annotation.text.lower()
    
    if any(keyword in text for keyword in ["rok", "miesiac", "norma", "imie", "nazwisko", "stanowisko", "dzien", "m-ca", "rozpoczecie", "pracy", "zakonczenie", "ilosc", "godzin", "notatka", "podpis"]):
        return SHIFT_HOURS
    elif any(keyword in text for keyword in ["stawka", "vat", "netto", "suma", "koncowa", "gg", "bar", "uslugi", "przekaski", "dodatki", "nasza", "wodka", "woda", "23", "23%", "8", "8%", "rach"]):
        return SHIFT_REPORT
    
    print(f"DEBUG: Uncategorized text found: {text[:500]}...") 
    return "uncategorized"



def send_email(subject, message_body):
    """
    General purpose email sender for notifications and errors.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    sender_email = os.getenv("SENDER_EMAIL")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not all([smtp_server, smtp_port, sender_email, receiver_email, email_password]):
        print("CRITICAL: Email configuration missing in environment variables.")
        return

    try:
        smtp_port = int(smtp_port)
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = f"<{os.urandom(16).hex()}@{sender_email.split('@')[-1]}>"

        html = f"""
        <html>
            <body>
                <h3>{subject}</h3>
                <p>Hello,</p>
                <p>{message_body}</p>
                <p>Regards,<br>Automated Financial Agent</p>
            </body>
        </html>
        """

        mime_text = MIMEText(html, 'html')
        msg.attach(mime_text)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, email_password)
            server.send_message(msg)
        print(f"Email notification sent: {subject}")

    except Exception as e:
        print(f"FAILED to send email: {e}")

def process_drive_images():
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    data_bucket_name = os.getenv("DATA_BUCKET")
    
    if not folder_id or not data_bucket_name:
        raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or DATA_BUCKET environment variables")

    print(f"Starting image ingestion from Drive folder: {folder_id}")
    drive_service = get_drive_service()
    vision_client = vision.ImageAnnotatorClient()
    storage_client = storage.Client()
    bucket = storage_client.bucket(data_bucket_name)


    now = datetime.datetime.now()
    last_month = now - relativedelta(months=1)
    month_year = last_month.strftime("%B%Y").lower()

    # List files in the folder
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'image/'",
        fields="files(id, name, mimeType)"
    ).execute()
    files = results.get('files', [])

    if not files:
        print("No image files found in the specified folder.")
        return

    processed_count = 0
    for file in files:
        file_id = file['id']
        file_name = file['name']
        print(f"Processing image: {file_name} ({file_id})")

        # Download file content
        request = drive_service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        content = file_content.getvalue()

        # Categorize
        category = categorize_image(vision_client, content)
        print(f"Image categorized as: {category}")
        
        # Determine GCS path
        gcs_path = f"{month_year}/{category}/{file_name}"
        
        # Upload to GCS
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(content, content_type=file['mimeType'])
        print(f"Successfully uploaded to: gs://{data_bucket_name}/{gcs_path}")
        processed_count += 1
    
    print(f"Finished processing {processed_count} images.")

@functions_framework.http
def main_handler(request):
    try:
        print("Pipeline triggered. Sending start notification...")
        send_email(
            subject="Monthly Financial Report - Ingestion Started",
            message_body="The <b>Automated Financial Agent</b> has started the monthly ingestion process."
        )

        process_drive_images()
        
        return "Process completed successfully", 200

    except Exception as e:
        error_msg = f"An error occurred during pipeline execution:\n{str(e)}"
        print(f"ERROR: {error_msg}")
        
        send_email(
            subject="ALERT: Monthly Financial Report Failed",
            message_body=f"The ingestion process failed with the following error:<br><br><b>{str(e)}</b><br><br>Please check the Google Cloud Console logs for more details."
        )
        
        return f"Error: {e}", 500
