import os
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("GMAIL_USER")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

FILTER_SENDER = "ashutosharma78@gmail.com"

# ✅ Simple sentiment rules
POSITIVE_KEYWORDS = [
    "approved", "verified", "looks good", "ok", "okay",
    "confirmed", "matched", "correct", "valid"
]

NEGATIVE_KEYWORDS = [
    "not matched", "incorrect", "rejected", "failed",
    "discrepancy", "issue", "mismatch", "error", "problem"
]

def analyze_sentiment(text: str):
    text = text.lower()

    for word in NEGATIVE_KEYWORDS:
        if word in text:
            return "NEGATIVE"

    for word in POSITIVE_KEYWORDS:
        if word in text:
            return "POSITIVE"

    return "NEUTRAL"


def read_latest_mail():
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(EMAIL, APP_PASSWORD)
        imap.select("inbox")

        status, messages = imap.search(None, f'(FROM "{FILTER_SENDER}")')

        if status != "OK" or not messages[0]:
            return {"message": "No emails found from sender"}

        mail_ids = messages[0].split()
        latest_email_id = mail_ids[-1]

        _, msg_data = imap.fetch(latest_email_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Decode subject
        subject_raw = msg.get("Subject", "")
        decoded_subject = decode_header(subject_raw)[0]
        subject, encoding = decoded_subject

        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")

        # ✅ Get sender
        _, sender_email = parseaddr(msg.get("From"))

        # ✅ Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        # ✅ Sentiment detection
        sentiment = analyze_sentiment(body)

        imap.logout()

        return {
            "from": sender_email,
            "subject": subject,
            "body": body.strip(),
            "sentiment": sentiment,
            "next_action": "AUTO_PROCESS" if sentiment == "POSITIVE" else "MANUAL_HR"
        }

    except Exception as e:
        return {"error": str(e)}


# ---------- Run directly ----------
if __name__ == "__main__":
    result = read_latest_mail()

    if "error" in result:
        print("❌ Error:", result["error"])
    elif "message" in result:
        print("ℹ️", result["message"])
    else:
        print("\n📩 HR Reply Analysis")
        print("=" * 50)
        print(f"From      : {result['from']}")
        print(f"Subject   : {result['subject']}")
        print(f"Sentiment : {result['sentiment']}")
        print(f"Action    : {result['next_action']}")
        print("-" * 50)
        print(result["body"])
