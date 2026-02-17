import os
import smtplib
import functions_framework
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

@functions_framework.http
def send_monthly_reminder(request):
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT"))
        sender_email = os.getenv("SENDER_EMAIL")
        receiver_email = os.getenv("RECEIVER_EMAIL")
        email_password = os.getenv("EMAIL_PASSWORD")

        if not all([sender_email, receiver_email, email_password]):
            return "Configuration missing", 500

        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "Monthly Financial Report - Ingestion Started"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = f"<{os.urandom(16).hex()}@{sender_email.split('@')[-1]}>"

        html = """
        <html>
            <head></head>
            <body>
                <h3>Monthly Financial Report Ingestion</h3>
                <p>Hello,</p>
                <p>This is an automated notification that the <b>Automated Financial Agent</b> has started the monthly ingestion process.</p>
                <p>Regards,<br>Automated Financial Agent</p>
            </body>
        </html>
        """

        mime_text = MIMEText(html, 'html')

        msg.attach(mime_text)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, email_password)
            server.send_message(msg)

        return "Email sent successfully", 200

    except Exception as e:
        return f"Error: {e}", 500