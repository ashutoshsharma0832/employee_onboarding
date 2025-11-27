# import os
# import json
# import re
# from typing import Optional, List, Dict

# from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
# from pydantic import BaseModel, ValidationError
# from bson import ObjectId
# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles

# from send_mail import send_email
# from sentimentanalysis import read_latest_mail
# from db import get_db_client

# load_dotenv()

# app = FastAPI()
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# # ---------------- CORS ----------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ---------------- CONFIG ----------------
# MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
# UPLOAD_BASE_DIR = "uploads"
# HR_EMAIL = os.getenv("HR_EMAIL", "ashutosharma78@gmail.com")

# client = AsyncIOMotorClient(MONGO_URL)
# db = client["employee_db"]

# # ---------------- MODELS ----------------
# class Metadata(BaseModel):
#     candidateName: str
#     email: str
#     employer: Optional[str] = None
#     phonenumber: Optional[str] = None
#     city: Optional[str] = None

# class Documents(BaseModel):
#     pendingFiles: Dict[str, str] = {}

# class EmployeePayload(BaseModel):
#     metadata: Metadata
#     documents: Documents
#     status: str

# class EmailRequest(BaseModel):
#     to: str
#     subject: str
#     body: str

# # ---------------- STARTUP ----------------
# @app.on_event("startup")
# async def startup():
#     app.state.collection = db["candidates"]

# def serialize_doc(doc):
#     doc["_id"] = str(doc["_id"])
#     return doc

# # ---------------- HEALTH ----------------
# @app.get("/")
# def health_check():
#     return {"status": "API running"}

# # ---------------- SEND MAIL ----------------
# @app.post("/send-mail")
# def send_mail_api(req: EmailRequest):
#     try:
#         send_email(req.to, req.subject, req.body)
#         return {"message": "Email sent successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------- READ LATEST MAIL ----------------
# @app.get("/read-latest-mail")
# def read_mail_api():
#     return read_latest_mail()

# # ---------------- CREATE CANDIDATE ----------------
# @app.post("/candidates")
# async def create_candidate(request: Request):
#     try:
#         data = await request.json()
#     except:
#         form = await request.form()
#         data = dict(form)

#     candidateName = data.get("candidateName")
#     email = data.get("email")
#     employer = data.get("employer")
#     city = data.get("city")
#     phonenumber = data.get("phonenumber") or data.get("phoneNumber") or ""

#     if not candidateName or not email:
#         raise HTTPException(status_code=400, detail="candidateName and email required")

#     data_to_insert = {
#         "metadata": {
#             "candidateName": candidateName,
#             "email": email,
#             "employer": employer,
#             "phonenumber": phonenumber,
#             "city": city
#         },
#         "documents": {"pendingFiles": {}},
#         "status": "QUEUED",
#         "hr_status": "PENDING",
#         "discrepancy_remark": ""
#     }

#     result = await app.state.collection.insert_one(data_to_insert)

#     # Email HR
#     send_email(
#         HR_EMAIL,
#         "New Candidate Verification",
#         f"ID: {str(result.inserted_id)}\nReply APPROVED / REJECTED"
#     )

#     return {"message": "Candidate created", "id": str(result.inserted_id)}

# # ---------------- INGEST FILES ----------------
# @app.post("/ingest-files")
# async def ingest_files(
#     metadata_json: str = Form(...),
#     files: Optional[List[UploadFile]] = File(None)
# ):
#     payload_data = json.loads(metadata_json)
#     metadata = Metadata(**payload_data.get("metadata", {}))
#     doc_types = payload_data.get("doc_types", [])

#     initial_payload = {
#         "metadata": metadata.model_dump(),
#         "documents": {"pendingFiles": {}},
#         "status": "QUEUED",
#         "hr_status": "PENDING",
#         "discrepancy_remark": ""
#     }

#     result = await app.state.collection.insert_one(initial_payload)
#     check_id = str(result.inserted_id)

#     send_email(
#         metadata.email,
#         "Documents Received",
#         f"Tracking ID: {check_id}"
#     )

#     # Save files
#     if files:
#         pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
#         os.makedirs(pending_dir, exist_ok=True)
#         pending_files_map = {}

#         for doc_key, file in zip(doc_types, files):
#             if not file.filename:
#                 continue

#             safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
#             path = os.path.join(pending_dir, f"{check_id}_{doc_key}_{safe_name}")

#             with open(path, "wb") as f:
#                 content = await file.read()
#                 f.write(content)

#             pending_files_map[doc_key] = path.replace("\\", "/")

#         await app.state.collection.update_one(
#             {"_id": result.inserted_id},
#             {"$set": {"documents.pendingFiles": pending_files_map}}
#         )

#     return {"message": "Queued", "check_id": check_id}

# # ---------------- CHECK STATUS ----------------
# @app.get("/check-status/{check_id}")
# async def get_status(check_id: str):
#     oid = ObjectId(check_id)
#     record = await app.state.collection.find_one({"_id": oid})
#     if not record:
#         raise HTTPException(status_code=404, detail="Not found")
#     return serialize_doc(record)

# # ---------------- LIST CANDIDATES ----------------
# @app.get("/candidates")
# async def list_candidates():
#     cursor = app.state.collection.find({})
#     result = []
#     async for doc in cursor:
#         result.append(serialize_doc(doc))
#     return {"candidates": result}

# # ---------------- UPDATE STATUS FROM HR MAIL ----------------
# @app.post("/update-status-from-hr/{candidate_id}")
# async def update_status_from_hr(candidate_id: str):
#     oid = ObjectId(candidate_id)
#     mail = read_latest_mail()

#     body = mail.get("body", "").upper()
#     status = "QUEUED"
#     hr_status = "PENDING"
#     remark = ""

#     if "APPROVED" in body:
#         status = "COMPLETED"
#         hr_status = "APPROVED"

#     elif "REJECTED" in body:
#         status = "DISCREPANCY"
#         hr_status = "REJECTED"
#         remark = body

#     await app.state.collection.update_one(
#         {"_id": oid},
#         {"$set": {
#             "status": status,
#             "hr_status": hr_status,
#             "discrepancy_remark": remark
#         }}
#     )

#     return {
#         "message": "HR mail processed",
#         "new_status": status,
#         "hr_status": hr_status
#     }

# # ---------------- PROCESS HR MAIL (GLOBAL) ----------------
# @app.post("/process-hr-mail")
# async def process_hr_mail():
#     mail = read_latest_mail()

#     email = mail.get("email")
#     body = mail.get("body", "").upper()

#     status = "QUEUED"
#     hr_status = "PENDING"
#     remark = ""

#     if "APPROVED" in body:
#         status = "COMPLETED"
#         hr_status = "APPROVED"

#     elif "REJECTED" in body:
#         status = "DISCREPANCY"
#         hr_status = "REJECTED"
#         remark = body

#     result = await app.state.collection.update_one(
#         {"metadata.email": email},
#         {"$set": {
#             "status": status,
#             "hr_status": hr_status,
#             "discrepancy_remark": remark
#         }}
#     )

#     return {
#         "matched": result.matched_count,
#         "updated": result.modified_count,
#         "status": status
#     }



#new###############################working


# import os
# import json
# import re
# from typing import Optional, List, Dict

# from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
# from pydantic import BaseModel
# from bson import ObjectId
# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles

# # ✅ IMPORT YOUR OWN MODULES
# from send_mail_hr import send_email
# from sentimentanalysis import read_latest_mail, analyze_sentiment

# load_dotenv()

# app = FastAPI()
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# # ---------------- CORS ----------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ---------------- CONFIG ----------------
# MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
# UPLOAD_BASE_DIR = "uploads"

# client = AsyncIOMotorClient(MONGO_URL)
# db = client["employee_db"]

# # ---------------- MODELS ----------------
# class Metadata(BaseModel):
#     candidateName: str
#     email: str
#     employer: Optional[str] = None
#     previous_hr_email: Optional[str] = None
#     phonenumber: Optional[str] = None
#     city: Optional[str] = None

# class Documents(BaseModel):
#     pendingFiles: Dict[str, str] = {}

# class EmployeePayload(BaseModel):
#     metadata: Metadata
#     documents: Documents
#     status: str
#     discrepancy_remark: str = ""

# class EmailRequest(BaseModel):
#     to: str
#     subject: str
#     body: str

# # ---------------- STARTUP ----------------
# @app.on_event("startup")
# async def startup():
#     app.state.collection = db["candidates"]

# def serialize_doc(doc):
#     doc["_id"] = str(doc["_id"])
#     return doc

# # ---------------- HEALTH ----------------
# @app.get("/")
# def health_check():
#     return {"status": "API running"}

# # ---------------- SEND MAIL API ----------------
# @app.post("/send-mail")
# def send_mail_api(req: EmailRequest):
#     try:
#         send_email(req.to, req.subject, req.body)
#         return {"message": "Email sent"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------- CREATE CANDIDATE ----------------
# @app.post("/candidates")
# async def create_candidate(request: Request):
#     data = await request.json()

#     candidateName = data.get("candidateName")
#     email = data.get("email")
#     employer = data.get("employer")
#     previous_hr_email = data.get("previous_hr_email")
#     city = data.get("city")
#     phonenumber = data.get("phonenumber", "")

#     if not candidateName or not email:
#         raise HTTPException(status_code=400, detail="candidateName and email required")

#     payload = {
#         "metadata": {
#             "candidateName": candidateName,
#             "email": email,
#             "employer": employer,
#             "previous_hr_email": previous_hr_email,
#             "phonenumber": phonenumber,
#             "city": city
#         },
#         "documents": {"pendingFiles": {}},
#         "status": "QUEUED",
#         "discrepancy_remark": ""
#     }

#     result = await app.state.collection.insert_one(payload)

#     # ✅ Send candidate mail
#     try:
#         send_email(
#             receiver_email=email,
#             subject="Welcome to Background Verification",
#             body=f"Hi {candidateName}, please submit documents."
#         )
#     except Exception as e:
#         print("❌ Candidate mail error:", e)

#     # ✅ Send HR mail
#     if previous_hr_email:
#         try:
#             send_email(
#                 receiver_email=previous_hr_email,
#                 subject="Employment Verification Request",
#                 body=f"""
# Candidate Name: {candidateName}
# Candidate Email: {email}
# Employer: {employer}

# Please reply with APPROVED or REJECTED
# Tracking ID: {str(result.inserted_id)}
# """
#             )
#         except Exception as e:
#             print("❌ HR mail error:", e)

#     return {"message": "Candidate created", "id": str(result.inserted_id)}

# # ---------------- READ HR MAIL ----------------
# @app.get("/read-hr-mail")
# def read_hr_mail():
#     return read_latest_mail()

# # ---------------- PROCESS HR RESPONSE ----------------
# @app.post("/process-hr-mail")
# async def process_hr_mail():
#     mail = read_latest_mail()

#     if "error" in mail:
#         raise HTTPException(status_code=500, detail=mail["error"])

#     sender_email = mail.get("from")
#     body = mail.get("body", "").lower()

#     sentiment = analyze_sentiment(body)

#     body_lower = body.lower()

#     if "rejected" in body_lower:
#         status = "DISCREPANCY"
#         remark = body
#     elif "approved" in body_lower:
#         status = "COMPLETED"
#         remark = ""
#     else:
#         status = "PENDING"
#         remark = ""


#     result = await app.state.collection.update_one(
#         {"metadata.previous_hr_email": sender_email},
#         {"$set": {"status": status, "discrepancy_remark": remark}}
#     )

#     return {
#         "matched": result.matched_count,
#         "updated": result.modified_count,
#         "status": status
#     }

# # ---------------- CHECK STATUS ----------------
# @app.get("/check-status/{check_id}")
# async def get_status(check_id: str):
#     record = await app.state.collection.find_one({"_id": ObjectId(check_id)})
#     if not record:
#         raise HTTPException(status_code=404, detail="Record not found")
#     return serialize_doc(record)

# # ---------------- LIST CANDIDATES ----------------
# @app.get("/candidates")
# async def list_candidates():
#     candidates = []
#     cursor = app.state.collection.find({})
#     async for c in cursor:
#         candidates.append(serialize_doc(c))
#     return {"candidates": candidates}


#########################################################

# src/backend/main.py

import os
import json
import re
from typing import Optional, List, Dict

from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from send_mail_hr import send_email
from sentimentanalysis import read_latest_mail, analyze_sentiment

load_dotenv()

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- CONFIG ----------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
UPLOAD_BASE_DIR = "uploads"

client = AsyncIOMotorClient(MONGO_URL)
db = client["employee_db"]

# ---------------- MODELS ----------------
class Metadata(BaseModel):
    candidateName: str
    email: str
    employer: Optional[str] = None
    previous_hr_email: Optional[str] = None
    phonenumber: Optional[str] = None
    city: Optional[str] = None

class Documents(BaseModel):
    pendingFiles: Dict[str, str] = {}

class EmployeePayload(BaseModel):
    metadata: Metadata
    documents: Documents
    status: str
    discrepancy_remark: str = ""

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

# ---------------- STARTUP ----------------
@app.on_event("startup")
async def startup():
    app.state.collection = db["candidates"]

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc

# ---------------- HEALTH ----------------
@app.get("/")
def health_check():
    return {"status": "API running"}

# ---------------- SEND MAIL API ----------------
@app.post("/send-mail")
def send_mail_api(req: EmailRequest):
    try:
        send_email(req.to, req.subject, req.body)
        return {"message": "Email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- CREATE CANDIDATE ----------------
@app.post("/candidates")
async def create_candidate(request: Request):
    data = await request.json()

    candidateName = data.get("candidateName")
    email = data.get("email")
    employer = data.get("employer")
    previous_hr_email = data.get("previous_hr_email")
    city = data.get("city")
    phonenumber = data.get("phonenumber", "")

    if not candidateName or not email:
        raise HTTPException(status_code=400, detail="candidateName and email required")

    payload = {
        "metadata": {
            "candidateName": candidateName,
            "email": email,
            "employer": employer,
            "previous_hr_email": previous_hr_email,
            "phonenumber": phonenumber,
            "city": city
        },
        "documents": {"pendingFiles": {}},
        "status": "QUEUED",
        "discrepancy_remark": ""
    }

    result = await app.state.collection.insert_one(payload)
    check_id = str(result.inserted_id)

    # ---------------- SEND CANDIDATE MAIL ----------------
    try:
        print(f"Sending candidate email to: {email}")
        send_email(
            to=email,
            subject="Welcome to Background Verification",
            body=f"Hi {candidateName}, please submit documents. Your Tracking ID: {check_id}"
        )
    except Exception as e:
        print("❌ Candidate mail error:", e)

    # ---------------- SEND HR MAIL ----------------
    if previous_hr_email:
        try:
            print(f"Sending HR email to: {previous_hr_email}")
            send_email(
                to=previous_hr_email,
                subject="Employment Verification Request",
                body=f"""
Candidate Name: {candidateName}
Candidate Email: {email}
Employer: {employer}

Please reply with APPROVED or REJECTED.
Tracking ID: {check_id}
"""
            )
        except Exception as e:
            print("❌ HR mail error:", e)

    return {"message": "Candidate created", "id": check_id}

# ---------------- INGEST FILES ----------------
@app.post("/ingest-files")
async def ingest_files(
    metadata_json: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    payload_data = json.loads(metadata_json)
    metadata = Metadata(**payload_data.get("metadata", {}))
    doc_types = payload_data.get("doc_types", [])

    initial_payload = {
        "metadata": metadata.model_dump(),
        "documents": {"pendingFiles": {}},
        "status": "QUEUED",
        "discrepancy_remark": ""
    }

    result = await app.state.collection.insert_one(initial_payload)
    check_id = str(result.inserted_id)

    # ---------------- SEND CANDIDATE MAIL ----------------
    try:
        print(f"Sending candidate doc email to: {metadata.email}")
        send_email(
            to=metadata.email,
            subject="Documents Received",
            body=f"Tracking ID: {check_id}"
        )
    except Exception as e:
        print("❌ Candidate doc email failed:", e)

    # ---------------- SEND HR MAIL ----------------
    if metadata.previous_hr_email:
        try:
            print(f"Sending HR doc email to: {metadata.previous_hr_email}")
            send_email(
                to=metadata.previous_hr_email,
                subject="Employment Verification Request",
                body=f"Please verify candidate. Tracking ID: {check_id}"
            )
        except Exception as e:
            print("❌ HR doc email failed:", e)

    # ---------------- SAVE FILES ----------------
    if files:
        pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
        os.makedirs(pending_dir, exist_ok=True)
        pending_files_map = {}

        for doc_key, file in zip(doc_types, files):
            if not file.filename:
                continue

            safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
            path = os.path.join(pending_dir, f"{check_id}_{doc_key}_{safe_name}")

            with open(path, "wb") as f:
                content = await file.read()
                f.write(content)

            pending_files_map[doc_key] = path.replace("\\", "/")

        await app.state.collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"documents.pendingFiles": pending_files_map}}
        )

    return {"message": "Queued", "check_id": check_id}

# ---------------- READ HR MAIL ----------------
@app.get("/read-hr-mail")
def read_hr_mail():
    try:
        mail = read_latest_mail()
        return mail
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading HR mail: {e}")

# ---------------- PROCESS HR RESPONSE ----------------
@app.post("/process-hr-mail")
async def process_hr_mail():
    mail = read_latest_mail()

    if "error" in mail:
        raise HTTPException(status_code=500, detail=mail["error"])

    sender_email = mail.get("from")
    body = mail.get("body", "")

    # Determine status
    body_lower = body.lower()
    if "rejected" in body_lower:
        status = "DISCREPANCY"
        remark = body
    elif "approved" in body_lower:
        status = "COMPLETED"
        remark = ""
    else:
        status = "PENDING"
        remark = ""

    result = await app.state.collection.update_one(
        {"metadata.previous_hr_email": sender_email},
        {"$set": {"status": status, "discrepancy_remark": remark}}
    )

    return {
        "matched": result.matched_count,
        "updated": result.modified_count,
        "status": status
    }

# ---------------- CHECK STATUS ----------------
@app.get("/check-status/{check_id}")
async def get_status(check_id: str):
    record = await app.state.collection.find_one({"_id": ObjectId(check_id)})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return serialize_doc(record)

# ---------------- LIST CANDIDATES ----------------
@app.get("/candidates")
async def list_candidates():
    candidates = []
    cursor = app.state.collection.find({})
    async for c in cursor:
        candidates.append(serialize_doc(c))
    return {"candidates": candidates}
