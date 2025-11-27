# # read_mail.py
# import os
# import imaplib
# import email
# from email.header import decode_header
# from dotenv import load_dotenv

# # Load env variables
# load_dotenv()

# EMAIL = os.getenv("GMAIL_USER")
# APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
# FILTER_SENDER = "alinaaafzall30@gmail.com"


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

#         # Decode subject
#         subject_raw = msg.get("Subject", "")
#         decoded_subject = decode_header(subject_raw)[0]
#         subject_, encoding = decoded_subject

#         if isinstance(subject_, bytes):
#             subject_ = subject_.decode(encoding or "utf-8", errors="ignore")

#         # Extract full body
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
#             "from": msg.get("From"),
#             "subject": subject_,
#             "body": body
#         }

#     except Exception as e:
#         return {"error": str(e)}


# # ------------------ Display Email Nicely ------------------

# result = read_latest_mail()

# if "error" in result:
#     print("❌ Error:", result["error"])

# elif "message" in result:
#     print("ℹ️", result["message"])

# else:
#     print("\n📩 Latest Email (Full Conversation)")
#     print("=" * 50)
#     print(f"From   : {result['from']}")
#     print(f"Subject: {result['subject']}")
#     print("-" * 50)

#     print("\n📝 Full Message:")
#     print("-" * 50)
#     print(result["body"])

###################################

# import os
# import imaplib
# import email
# from dotenv import load_dotenv
# from motor.motor_asyncio import AsyncIOMotorClient

# load_dotenv()

# EMAIL = os.getenv("GMAIL_USER")
# APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
# MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

# client = AsyncIOMotorClient(MONGO_URL)
# db = client["employee_db"]
# collection = db["candidates"]

# def read_latest_mail():
#     try:
#         mail = imaplib.IMAP4_SSL("imap.gmail.com")
#         mail.login(EMAIL, APP_PASSWORD)
#         mail.select("inbox")

#         status, messages = mail.search(None, "ALL")
#         mail_ids = messages[0].split()

#         if not mail_ids:
#             return {"message": "No emails found"}

#         latest_id = mail_ids[-1]
#         status, msg_data = mail.fetch(latest_id, "(RFC822)")

#         for response_part in msg_data:
#             if isinstance(response_part, tuple):
#                 msg = email.message_from_bytes(response_part[1])

#                 from_email = msg.get("From", "")

#                 # ✅ Find candidate by email
#                 candidate = collection.find_one({
#                     "metadata.email": {"$regex": from_email}
#                 })

#                 if candidate:
#                     collection.update_one(
#                         {"_id": candidate["_id"]},
#                         {"$set": {"status": "COMPLETED"}}
#                     )

#         return {"message": "Email processed & status updated to COMPLETED"}

#     except Exception as e:
#         return {"error": str(e)}

#######################################

import os
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("GMAIL_USER")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Change this to HR email or candidate email
FILTER_SENDER = "hksinghal1604@gmail.com"

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

        # ✅ Decode subject safely
        subject_raw = msg.get("Subject", "")
        decoded_subject = decode_header(subject_raw)[0]
        subject_, encoding = decoded_subject
        if isinstance(subject_, bytes):
            subject_ = subject_.decode(encoding or "utf-8", errors="ignore")

        # ✅ Extract clean sender email
        _, sender_email = parseaddr(msg.get("From"))

        # ✅ Extract full text body
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
            "from": sender_email,
            "subject": subject_,
            "body": body
        }

    except Exception as e:
        return {"error": str(e)}


# ---------- Run Directly ----------
if __name__ == "__main__":
    result = read_latest_mail()

    if "error" in result:
        print("❌ Error:", result["error"])
    elif "message" in result:
        print("ℹ️", result["message"])
    else:
        print("\n📩 Latest Email")
        print("=" * 50)
        print(f"From   : {result['from']}")
        print(f"Subject: {result['subject']}")
        print("-" * 50)
        print(result["body"])
