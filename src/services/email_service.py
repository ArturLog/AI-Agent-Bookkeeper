import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, RECEIVER_EMAIL, EMAIL_PASSWORD

class EmailService:
    @staticmethod
    def send_email(subject: str, message_body: str) -> None:
        """
        General purpose email sender for notifications and errors.
        """
        if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, RECEIVER_EMAIL, EMAIL_PASSWORD]):
            print("CRITICAL: Email configuration missing in environment variables.")
            return

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECEIVER_EMAIL
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = f"<{os.urandom(16).hex()}@{SENDER_EMAIL.split('@')[-1]}>"

            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <h3 style="color: #2c3e50;">{subject}</h3>
                    <p>Hello,</p>
                    <p>{message_body}</p>
                    <p style="margin-top: 20px; font-weight: bold;">Regards,<br>Automated Financial Agent</p>
                </body>
            </html>
            """

            mime_text = MIMEText(html, 'html')
            msg.attach(mime_text)

            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SENDER_EMAIL, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"Email notification sent: {subject}")

        except Exception as e:
            print(f"FAILED to send email: {e}")
