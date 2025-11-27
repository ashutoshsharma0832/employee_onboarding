import os
import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

from dotenv import load_dotenv
load_dotenv()

EMAIL_ADDRESS = os.getenv("OUTLOOK_EMAIL")      # e.g. noreply@tridentinfo.com
EMAIL_PASSWORD = os.getenv("OUTLOOK_PASSWORD")  # e.g. reply@#$2026


def send_mail(to_email, subject, body):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError("Set OUTLOOK_EMAIL and OUTLOOK_PASSWORD environment variables first")

    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()  # upgrade to secure connection
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    send_mail(
        to_email="achahal023@gmail.com",
        subject="Test mail from Python",
        body="Hi,\n\nThis is a test email sent from Python using Outlook SMTP.\n\nRegards,\nAnkit"
    )
