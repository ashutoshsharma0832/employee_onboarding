# test_imap_login.py
import os
import imaplib
from dotenv import load_dotenv

load_dotenv()

IMAP_SERVER = "outlook.office365.com"
IMAP_PORT = 993
OUTLOOK_EMAIL = os.getenv("OUTLOOK_EMAIL")
OUTLOOK_PASSWORD = os.getenv("OUTLOOK_PASSWORD")

print("Email:", OUTLOOK_EMAIL)
print("Password length:", len(OUTLOOK_PASSWORD) if OUTLOOK_PASSWORD else 0)

imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
imap.debug = 4  # verbose output, optional
imap.login(OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
print("LOGIN OK")
imap.logout()
