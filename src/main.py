import os
import smtplib
import functions_framework
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@functions_framework.http
def send_monthly_reminder(request):
    try:
        smtp_server = os.environ.get("SMTP_SERVER")
        smtp_port = int(os.environ.get("SMTP_PORT"))
        sender_email = os.environ.get("SENDER_EMAIL")
        receiver_email = os.environ.get("RECEIVER_EMAIL")
        email_password = os.environ.get("EMAIL_PASSWORD")

        if not all([sender_email, receiver_email, email_password]):
            return "Configuration missing", 500

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "Start Monthly Financial Report"

        body = """
        <html>
          <body>
            <h3>It's the 1st of the month!</h3>
            <p>The Automated Financial Agent has started the ingestion process.</p>
            <p>Please check the Telegram channel and wait for the verification link.</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, email_password)
            server.send_message(msg)

        return "Email sent successfully", 200

    except Exception as e:
        return f"Error: {e}", 500