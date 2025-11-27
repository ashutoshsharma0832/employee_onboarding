# import os
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from email.mime.base import MIMEBase
# from email import encoders
# from dotenv import load_dotenv

# load_dotenv()

# SENDER_EMAIL = os.getenv("GMAIL_USER")
# APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# def send_email(receiver_email: str, subject: str, body: str, attachments: list):
#     if not receiver_email:
#         raise Exception("Receiver email is missing")

#     # Create multipart message
#     msg = MIMEMultipart()
#     msg['From'] = SENDER_EMAIL
#     msg['To'] = receiver_email
#     msg['Subject'] = subject

#     # Add body
#     msg.attach(MIMEText(body, 'plain'))

#     # Attach files
#     for file_path in attachments:
#         if not os.path.exists(file_path):
#             raise Exception(f"Attachment not found: {file_path}")

#         with open(file_path, "rb") as f:
#             part = MIMEBase('application', 'octet-stream')
#             part.set_payload(f.read())

#         encoders.encode_base64(part)
#         file_name = os.path.basename(file_path)

#         part.add_header(
#             'Content-Disposition',
#             f'attachment; filename="{file_name}"'
#         )

#         msg.attach(part)

#     try:
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(SENDER_EMAIL, APP_PASSWORD)
#         server.send_message(msg)
#         server.quit()
#         print("Email sent successfully")
#         return True
#     except Exception as e:
#         raise Exception(f"Email error: {e}")


# # ---- USAGE ----
# send_email(
#     receiver_email="hksinghal1604@gmail.com",
#     subject="Employee Background Verification",
#     body="Kindly verify",
#     attachments=[
#         r"D:\employee-onboarding\Rex-Omni-Universal-Vision-Intelligence.pdf",
#         # r"D:\docs\file2.docx"
#     ]
# )


#######################################

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("GMAIL_USER")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def send_email(receiver_email: str, subject: str, body: str, attachments: list = None):
    if not receiver_email:
        raise Exception("Receiver email is missing")

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # If attachments exist
    if attachments:
        for file_path in attachments:
            if not os.path.exists(file_path):
                raise Exception(f"Attachment not found: {file_path}")

            with open(file_path, "rb") as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            file_name = os.path.basename(file_path)

            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{file_name}"'
            )

            msg.attach(part)

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
