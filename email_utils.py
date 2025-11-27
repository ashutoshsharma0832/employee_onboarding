# mailer.py
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

EMAIL_ADDRESS = os.getenv("OUTLOOK_EMAIL")      # e.g. noreply@tridentinfo.com
EMAIL_PASSWORD = os.getenv("OUTLOOK_PASSWORD")  # e.g. reply@#$2026


def send_mail(to_email: str, subject: str, body: str):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError("Set OUTLOOK_EMAIL and OUTLOOK_PASSWORD env vars first")

    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
