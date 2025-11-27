# import os
# import smtplib
# from email.mime.text import MIMEText
# from dotenv import load_dotenv

# load_dotenv()

# SENDER_EMAIL = os.getenv("GMAIL_USER")
# APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
# receiver_email = "mafiaking05041998@gmail.com"

# msg = MIMEText("This is a testing mail")
# msg['Subject'] = "Test Email"
# msg['From'] = SENDER_EMAIL
# msg['To'] = receiver_email

# try:
#     server = smtplib.SMTP("smtp.gmail.com", 587)
#     server.starttls()
#     server.login(SENDER_EMAIL, APP_PASSWORD)
#     server.send_message(msg)
#     server.quit()
#     print("Email sent successfully")
# except Exception as e:
#     print("Error sending email:", e)

# send_mail.py
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("GMAIL_USER")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def send_email(receiver_email: str, subject: str, body: str):
    if not receiver_email:
        raise Exception("Receiver email is missing")

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")
        return True
    except Exception as e:
        raise Exception(f"Email error: {e}")



send_email(
    receiver_email="alinaaafzall30@gmail.com",
    subject="Test Mail",
    body="This is a Test Mail"
)