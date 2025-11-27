# import os
# import imaplib
# import email
# from email.header import decode_header
# from email.utils import parseaddr
# from dotenv import load_dotenv
 
# load_dotenv()
 
# EMAIL = os.getenv("GMAIL_USER")
# APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
 
# # Change this to HR email or candidate email
# FILTER_SENDER = "ashutosharma78@gmail.com"
 
# def read_latest_mail():
#     try:
#         imap = imaplib.IMAP4_SSL("imap.gmail.com")
#         imap.login(EMAIL, APP_PASSWORD)
#         imap.select("inbox")
 
#         status, messages = imap.search(None, f'(FROM "{FILTER_SENDER}")')
 
#         if status != "OK" or not messages[0]:
#             return {"message": "No emails found from sender"}
 
#         mail_ids = messages[0].split()
#         latest_email_id = mail_ids[-1]
 
#         _, msg_data = imap.fetch(latest_email_id, "(RFC822)")
#         raw_email = msg_data[0][1]
#         msg = email.message_from_bytes(raw_email)
 
#         # ✅ Decode subject safely
#         subject_raw = msg.get("Subject", "")
#         decoded_subject = decode_header(subject_raw)[0]
#         subject_, encoding = decoded_subject
#         if isinstance(subject_, bytes):
#             subject_ = subject_.decode(encoding or "utf-8", errors="ignore")
 
#         # ✅ Extract clean sender email
#         _, sender_email = parseaddr(msg.get("From"))
 
#         # ✅ Extract full text body
#         body = ""
#         if msg.is_multipart():
#             for part in msg.walk():
#                 if part.get_content_type() == "text/plain":
#                     body = part.get_payload(decode=True).decode(errors="ignore")
#                     break
#         else:
#             body = msg.get_payload(decode=True).decode(errors="ignore")
 
#         imap.logout()
 
#         return {
#             "from": sender_email,
#             "subject": subject_,
#             "body": body
#         }
 
#     except Exception as e:
#         return {"error": str(e)}
 
 
# # ---------- Run Directly ----------
# if __name__ == "__main__":
#     result = read_latest_mail()
 
#     if "error" in result:
#         print("❌ Error:", result["error"])
#     elif "message" in result:
#         print("ℹ️", result["message"])
#     else:
#         print("\n📩 Latest Email")
#         print("=" * 50)
#         print(f"From   : {result['from']}")
#         print(f"Subject: {result['subject']}")
#         print("-" * 50)
#         print(result["body"])
##################################

import imaplib
import email
import os
from email.header import decode_header
from email.utils import parseaddr
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("GMAIL_USER")
PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# ✅ Put HR mail here
os.getenv("HR_EMAIL", "ashutosharma78@gmail.com")

def read_latest_hr_mail():
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(EMAIL, PASSWORD)
        imap.select("inbox")

        # ✅ Only fetch mails from HR
        status, data = imap.search(None, f'(FROM "{HR_EMAIL}")')

        if status != "OK" or not data[0]:
            return None

        ids = data[0].split()
        latest_id = ids[-1]

        _, msg_data = imap.fetch(latest_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        # Extract sender safely
        _, sender = parseaddr(msg.get("From"))

        # ✅ Extract text body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        imap.logout()

        return {
            "from": sender,
            "body": body.strip()
        }

    except Exception as e:
        return {"error": str(e)}
