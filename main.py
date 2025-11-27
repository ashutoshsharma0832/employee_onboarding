# # main.py

# # --- Standard Library Imports ---
# import os
# import json
# import re
# from datetime import datetime
# from typing import List, Optional, Dict, Any

# # --- Third-Party Imports ---
# from fastapi import FastAPI, HTTPException, UploadFile, File, Form, staticfiles
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import ValidationError
# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# from bson import ObjectId

# # --- Local Application Imports ---
# from schemas import EmployeePayload, Metadata, Documents
# from utils import serialize_doc, serialize_docs

# # ----------------------------- Env & App Configuration -----------------------------
# load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
# MONGODB_DB = os.getenv("MONGODB_DB", "mydb")
# MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "employees")
# UPLOAD_BASE_DIR = os.getenv("UPLOAD_BASE_DIR", "./uploads")

# app = FastAPI(title="Employee Document Ingest API")

# app.mount("/static", staticfiles.StaticFiles(directory=UPLOAD_BASE_DIR), name="static")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ----------------------------- DB Lifecycle Events -----------------------------
# @app.on_event("startup")
# async def _startup():
#     """Initializes DB connection and ensures upload directories exist."""
#     os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)
#     app.state.client = AsyncIOMotorClient(MONGODB_URI)
#     app.state.db = app.state.client[MONGODB_DB]
#     app.state.collection = app.state.db[MONGODB_COLLECTION]

# @app.on_event("shutdown")
# async def _shutdown():
#     """Closes the database connection gracefully."""
#     if getattr(app.state, "client", None):
#         app.state.client.close()

# # ----------------------------- Health Check Endpoint -----------------------------
# @app.get('/healthz')
# def health_check():
#     """A simple endpoint to confirm the API is running."""
#     return {"status": "ok"}

# # ----------------------------- API Endpoints -----------------------------

# @app.post("/ingest-files")
# async def ingest_files(
#     metadata_json: str = Form(..., description='JSON string for metadata and file info.'),
#     files: Optional[List[UploadFile]] = File(None, description="Uploaded files."),
# ):
#     """
#     Accepts candidate metadata and files, queues them for background processing,
#     and returns immediately with a unique ID for status tracking.
#     """
#     try:
#         payload_data = json.loads(metadata_json)
#         metadata = Metadata(**payload_data.get("metadata", {}))
#         doc_types = payload_data.get("doc_types", [])
#     except (json.JSONDecodeError, ValidationError) as e:
#         raise HTTPException(status_code=400, detail=f"Invalid metadata_json format: {e}")

#     documents_object = Documents(pendingFiles={})

#     initial_payload = EmployeePayload(
#         metadata=metadata,
#         documents=documents_object,
#         status="QUEUED"
#     )

#     result = await app.state.collection.insert_one(initial_payload.model_dump(exclude_unset=True))
#     check_id = str(result.inserted_id)

#     if not files:
#         await app.state.collection.update_one(
#             {"_id": result.inserted_id},
#             {"$set": {"status": "COMPLETED"}}
#         )
#         return {"message": "Request accepted. No files to process.", "check_id": check_id, "status": "COMPLETED"}

#     pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
#     os.makedirs(pending_dir, exist_ok=True)
    
#     pending_files_map = {}
#     for doc_key, file in zip(doc_types, files):
#         if not file.filename: continue
#         safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
#         pending_path = os.path.join(pending_dir, f"{check_id}_{doc_key}_{safe_filename}")
        
#         with open(pending_path, "wb") as f:
#             content = await file.read()
#             f.write(content)
        
#         pending_files_map[doc_key] = pending_path

#     await app.state.collection.update_one(
#         {"_id": result.inserted_id},
#         {"$set": {"documents.pendingFiles": pending_files_map}}
#     )

#     return {"message": "Request queued successfully.", "check_id": check_id, "status": "QUEUED"}

# @app.get("/check-status/{check_id}")
# async def get_check_status(check_id: str):
#     """
#     Retrieves the processing status and data for a specific background check.
#     """
#     try:
#         oid = ObjectId(check_id)
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid check_id format.")
        
#     record = await app.state.collection.find_one({"_id": oid})
    
#     if not record:
#         raise HTTPException(status_code=404, detail="Check ID not found.")
        
#     return serialize_doc(record)

# @app.get("/employees")
# async def get_employees(
#     page: int = 1,
#     limit: int = 10,
#     search: Optional[str] = None
# ):
#     """
#     Retrieves a paginated and searchable list of employee records,
#     formatted for the frontend candidate table.
#     """
#     if page < 1:
#         page = 1
#     if limit < 1 or limit > 100:
#         limit = 10

#     skip = (page - 1) * limit
#     query: Dict[str, Any] = {}

#     # Search by candidateName / email / employer / phone / city (optional)
#     if search:
#         search_regex = re.compile(search, re.IGNORECASE)
#         query["$or"] = [
#             {"metadata.candidateName": {"$regex": search_regex}},
#             {"metadata.email": {"$regex": search_regex}},
#             {"metadata.employer": {"$regex": search_regex}},
#             {"metadata.phoneNumber": {"$regex": search_regex}},
#             {"metadata.city": {"$regex": search_regex}},
#         ]

#     collection = app.state.collection
#     total_docs = await collection.count_documents(query)

#     cursor = (
#         collection
#         .find(query)
#         .sort("updatedAt", -1)
#         .skip(skip)
#         .limit(limit)
#     )
#     employees = await cursor.to_list(length=limit)

#     # ---- map DB docs -> frontend-friendly "candidates" ----
#     candidates = []
#     for emp in employees:
#         metadata = emp.get("metadata", {}) or {}

#         candidates.append({
#             "id": str(emp.get("_id")),
#             "candidateName": metadata.get("candidateName"),
#             "employer": metadata.get("employer"),
#             "phoneNumber": metadata.get("phoneNumber"),
#             "email": metadata.get("email"),
#             "city": metadata.get("city"),
#             # use backend status, default to "Pending" if missing
#             "status": emp.get("status") or "Pending",
#         })

#     # ---- final response ----
#     return {
#         "candidates": candidates,
#         "pagination": {
#             "currentPage": page,
#             "totalPages": (total_docs + limit - 1) // limit,
#             "totalEntries": total_docs,
#         },
#     }



# ################################################33
# import os
# import json
# import re
# from typing import Optional, List, Dict

# from fastapi import FastAPI, File, UploadFile, Form, HTTPException
# from pydantic import BaseModel, ValidationError
# from bson import ObjectId
# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# from fastapi.middleware.cors import CORSMiddleware

# from send_mail import send_email
# from read_email import read_latest_mail

# load_dotenv()

# app = FastAPI()

# # ---------------- CORS CONFIG (FIXED) ----------------

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "*",
#     ],
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

# # ---------------- HEALTH CHECK ----------------

# @app.get("/")
# def health_check():
#     return {"status": "API running"}

# # ---------------- SEND MAIL API ----------------

# @app.post("/send-mail")
# def send_mail_api(req: EmailRequest):
#     try:
#         send_email(
#             receiver_email=req.to,
#             subject=req.subject,
#             body=req.body
#         )
#         return {"message": "Email sent successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------- READ MAIL API ----------------

# @app.get("/read-latest-mail")
# def read_mail_api():
#     return read_latest_mail()

# # ---------------- INGEST FILES API ----------------

# @app.post("/ingest-files")
# async def ingest_files(
#     metadata_json: str = Form(...),
#     files: Optional[List[UploadFile]] = File(None)
# ):
#     try:
#         payload_data = json.loads(metadata_json)
#         metadata = Metadata(**payload_data.get("metadata", {}))
#         doc_types = payload_data.get("doc_types", [])
#     except (json.JSONDecodeError, ValidationError) as e:
#         raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

#     documents_object = Documents(pendingFiles={})

#     initial_payload = EmployeePayload(
#         metadata=metadata,
#         documents=documents_object,
#         status="QUEUED"
#     )

#     # Save to DB
#     result = await app.state.collection.insert_one(initial_payload.model_dump())
#     check_id = str(result.inserted_id)

#     # Auto send email
#     try:
#         send_email(
#             receiver_email=metadata.email,
#             subject="Documents Received",
#             body=f"""Hi {metadata.candidateName},

# We have received your details.
# Tracking ID: {check_id}

# Regards,
# HR Team"""
#         )
#     except Exception as e:
#         print("Email failed:", e)

#     # File saving
#     if files:
#         pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
#         os.makedirs(pending_dir, exist_ok=True)

#         pending_files_map = {}

#         for doc_key, file in zip(doc_types, files):
#             if not file.filename:
#                 continue

#             safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
#             pending_path = os.path.join(
#                 pending_dir, f"{check_id}_{doc_key}_{safe_filename}"
#             )

#             with open(pending_path, "wb") as f:
#                 content = await file.read()
#                 f.write(content)

#             pending_files_map[doc_key] = pending_path

#         await app.state.collection.update_one(
#             {"_id": result.inserted_id},
#             {"$set": {"documents.pendingFiles": pending_files_map}}
#         )

#     return {
#         "message": "Request queued successfully",
#         "check_id": check_id,
#         "status": "QUEUED"
#     }

# # ---------------- CHECK STATUS API ----------------

# @app.get("/check-status/{check_id}")
# async def get_status(check_id: str):
#     try:
#         oid = ObjectId(check_id)
#     except:
#         raise HTTPException(status_code=400, detail="Invalid ID")

#     record = await app.state.collection.find_one({"_id": oid})
#     if not record:
#         raise HTTPException(status_code=404, detail="Not found")

#     return serialize_doc(record)

#############################
# work





# import os
# import json
# import re
# from typing import Optional, List, Dict

# from fastapi import FastAPI, File, UploadFile, Form, HTTPException
# from pydantic import BaseModel, ValidationError
# from bson import ObjectId
# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# from fastapi.middleware.cors import CORSMiddleware

# from send_mail import send_email
# from read_email import read_latest_mail

# load_dotenv()

# app = FastAPI()

# # ---------------- CORS CONFIG (FIXED) ----------------

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "*",
#     ],
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

# # ---------------- HEALTH CHECK ----------------

# @app.get("/")
# def health_check():
#     return {"status": "API running"}

# # ---------------- SEND MAIL API ----------------

# @app.post("/send-mail")
# def send_mail_api(req: EmailRequest):
#     try:
#         send_email(
#             receiver_email=req.to,
#             subject=req.subject,
#             body=req.body
#         )
#         return {"message": "Email sent successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------- READ MAIL API ----------------

# @app.get("/read-latest-mail")
# def read_mail_api():
#     return read_latest_mail()

# # ---------------- INGEST FILES API ----------------

# @app.post("/ingest-files")
# async def ingest_files(
#     metadata_json: str = Form(...),
#     files: Optional[List[UploadFile]] = File(None)
# ):
#     try:
#         payload_data = json.loads(metadata_json)
#         metadata = Metadata(**payload_data.get("metadata", {}))
#         doc_types = payload_data.get("doc_types", [])
#     except (json.JSONDecodeError, ValidationError) as e:
#         raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

#     documents_object = Documents(pendingFiles={})

#     initial_payload = EmployeePayload(
#         metadata=metadata,
#         documents=documents_object,
#         status="QUEUED"
#     )

#     # Save to DB
#     result = await app.state.collection.insert_one(initial_payload.model_dump())
#     check_id = str(result.inserted_id)

#     # Auto send email
#     try:
#         send_email(
#             receiver_email=metadata.email,
#             subject="Documents Received",
#             body=f"""Hi {metadata.candidateName},

# We have received your details.
# Tracking ID: {check_id}

# Regards,
# HR Team"""
#         )
#     except Exception as e:
#         print("Email failed:", e)

#     # File saving
#     if files:
#         pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
#         os.makedirs(pending_dir, exist_ok=True)

#         pending_files_map = {}

#         for doc_key, file in zip(doc_types, files):
#             if not file.filename:
#                 continue

#             safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
#             pending_path = os.path.join(
#                 pending_dir, f"{check_id}_{doc_key}_{safe_filename}"
#             )

#             with open(pending_path, "wb") as f:
#                 content = await file.read()
#                 f.write(content)

#             pending_files_map[doc_key] = pending_path

#         await app.state.collection.update_one(
#             {"_id": result.inserted_id},
#             {"$set": {"documents.pendingFiles": pending_files_map}}
#         )

#     return {
#         "message": "Request queued successfully",
#         "check_id": check_id,
#         "status": "QUEUED"
#     }

# # ---------------- CHECK STATUS API ----------------

# @app.get("/check-status/{check_id}")
# async def get_status(check_id: str):
#     try:
#         oid = ObjectId(check_id)
#     except:
#         raise HTTPException(status_code=400, detail="Invalid ID")

#     record = await app.state.collection.find_one({"_id": oid})
#     if not record:
#         raise HTTPException(status_code=404, detail="Not found")

#     return serialize_doc(record)

# # ---------------- LIST ALL CANDIDATES ----------------

# @app.get("/candidates")
# async def list_candidates():
#     candidates_cursor = app.state.collection.find({})
#     candidates = []
#     async for doc in candidates_cursor:
#         candidates.append(serialize_doc(doc))
#     return {"candidates": candidates}


#######################################
# import os
# import json
# import re
# from typing import Optional, List, Dict

# from fastapi import FastAPI, File, UploadFile, Form, HTTPException
# from pydantic import BaseModel, ValidationError
# from bson import ObjectId
# from motor.motor_asyncio import AsyncIOMotorClient
# from dotenv import load_dotenv
# from fastapi.middleware.cors import CORSMiddleware

# from send_mail import send_email
# from read_email import read_latest_mail

# load_dotenv()

# app = FastAPI()

# # ---------------- CORS CONFIG ----------------

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

# # ---------------- HEALTH CHECK ----------------

# @app.get("/")
# def health_check():
#     return {"status": "API running"}

# # ---------------- SEND MAIL API ----------------

# @app.post("/send-mail")
# def send_mail_api(req: EmailRequest):
#     try:
#         send_email(
#             receiver_email=req.to,
#             subject=req.subject,
#             body=req.body
#         )
#         return {"message": "Email sent successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------- READ MAIL API ----------------

# @app.get("/read-latest-mail")
# def read_mail_api():
#     return read_latest_mail()

# # ---------------- POST /candidates ----------------

# @app.post("/candidates")
# async def create_candidate(
#     candidateName: str = Form(...),
#     email: str = Form(...),
#     employer: Optional[str] = Form(None),
#     phonenumber: Optional[str] = Form(None),
#     city: Optional[str] = Form(None),
# ):
#     data = {
#         "metadata": {
#             "candidateName": candidateName,
#             "email": email,
#             "employer": employer,
#             "phonenumber": phonenumber,
#             "city": city
#         },
#         "documents": {"pendingFiles": {}},
#         "status": "QUEUED"
#     }

#     result = await app.state.collection.insert_one(data)
#     return {
#         "message": "Candidate created",
#         "id": str(result.inserted_id)
#     }

# # ---------------- INGEST FILES API ----------------

# @app.post("/ingest-files")
# async def ingest_files(
#     metadata_json: str = Form(...),
#     files: Optional[List[UploadFile]] = File(None)
# ):
#     try:
#         payload_data = json.loads(metadata_json)
#         metadata = Metadata(**payload_data.get("metadata", {}))
#         doc_types = payload_data.get("doc_types", [])
#     except (json.JSONDecodeError, ValidationError) as e:
#         raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

#     documents_object = Documents(pendingFiles={})

#     initial_payload = EmployeePayload(
#         metadata=metadata,
#         documents=documents_object,
#         status="QUEUED"
#     )

#     result = await app.state.collection.insert_one(initial_payload.model_dump())
#     check_id = str(result.inserted_id)

#     # Auto send email
#     try:
#         send_email(
#             receiver_email=metadata.email,
#             subject="Documents Received",
#             body=f"""Hi {metadata.candidateName},

# We have received your details.
# Tracking ID: {check_id}

# Regards,
# HR Team"""
#         )
#     except Exception as e:
#         print("Email failed:", e)

#     # File saving
#     if files:
#         pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
#         os.makedirs(pending_dir, exist_ok=True)

#         pending_files_map = {}

#         for doc_key, file in zip(doc_types, files):
#             if not file.filename:
#                 continue

#             safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
#             pending_path = os.path.join(
#                 pending_dir, f"{check_id}_{doc_key}_{safe_filename}"
#             )

#             with open(pending_path, "wb") as f:
#                 content = await file.read()
#                 f.write(content)

#             pending_files_map[doc_key] = pending_path

#         await app.state.collection.update_one(
#             {"_id": result.inserted_id},
#             {"$set": {"documents.pendingFiles": pending_files_map}}
#         )

#     return {
#         "message": "Request queued successfully",
#         "check_id": check_id,
#         "status": "QUEUED"
#     }

# # ---------------- CHECK STATUS API ----------------

# @app.get("/check-status/{check_id}")
# async def get_status(check_id: str):
#     try:
#         oid = ObjectId(check_id)
#     except:
#         raise HTTPException(status_code=400, detail="Invalid ID")

#     record = await app.state.collection.find_one({"_id": oid})
#     if not record:
#         raise HTTPException(status_code=404, detail="Not found")

#     return serialize_doc(record)

# # ---------------- LIST ALL CANDIDATES ----------------

# @app.get("/candidates")
# async def list_candidates():
#     candidates_cursor = app.state.collection.find({})
#     candidates = []
#     async for doc in candidates_cursor:
#         candidates.append(serialize_doc(doc))
#     return {"candidates": candidates}

#####################################

import os
import json
import re
from typing import Optional, List, Dict

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from pydantic import BaseModel, ValidationError
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from send_mail import send_email
from read_email import read_latest_mail

load_dotenv()

app = FastAPI()

# ---------------- CORS CONFIG ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    phonenumber: Optional[str] = None
    city: Optional[str] = None

class Documents(BaseModel):
    pendingFiles: Dict[str, str] = {}

class EmployeePayload(BaseModel):
    metadata: Metadata
    documents: Documents
    status: str

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

# ---------------- HEALTH CHECK ----------------

@app.get("/")
def health_check():
    return {"status": "API running"}

# ---------------- SEND MAIL API ----------------

@app.post("/send-mail")
def send_mail_api(req: EmailRequest):
    try:
        send_email(
            receiver_email=req.to,
            subject=req.subject,
            body=req.body
        )
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- READ MAIL API ----------------

@app.get("/read-latest-mail")
def read_mail_api():
    return read_latest_mail()

# ---------------- POST /candidates ----------------

@app.post("/candidates")
async def create_candidate(request: Request):
    data = {}

    # Handle both JSON and FormData
    try:
        data = await request.json()
    except:
        form = await request.form()
        data = dict(form)

    candidateName = data.get("candidateName")
    email = data.get("email")
    employer = data.get("employer")
    city = data.get("city")

    # Accept both key formats
    phonenumber = data.get("phonenumber") or data.get("phoneNumber") or ""

    if not candidateName or not email:
        raise HTTPException(status_code=400, detail="candidateName and email are required")

    data_to_insert = {
        "metadata": {
            "candidateName": candidateName,
            "email": email,
            "employer": employer,
            "phonenumber": phonenumber,  # never null
            "city": city
        },
        "documents": {"pendingFiles": {}},
        "status": "QUEUED"
    }

    result = await app.state.collection.insert_one(data_to_insert)

    return {
        "message": "Candidate created",
        "id": str(result.inserted_id)
    }

# ---------------- INGEST FILES API ----------------

@app.post("/ingest-files")
async def ingest_files(
    metadata_json: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    try:
        payload_data = json.loads(metadata_json)
        metadata = Metadata(**payload_data.get("metadata", {}))
        doc_types = payload_data.get("doc_types", [])
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    documents_object = Documents(pendingFiles={})

    initial_payload = EmployeePayload(
        metadata=metadata,
        documents=documents_object,
        status="QUEUED"
    )

    result = await app.state.collection.insert_one(initial_payload.model_dump())
    check_id = str(result.inserted_id)

    # Auto send email
    try:
        send_email(
            receiver_email=metadata.email,
            subject="Documents Received",
            body=f"""Hi {metadata.candidateName},

We have received your details.
Tracking ID: {check_id}

Regards,
HR Team"""
        )
    except Exception as e:
        print("Email failed:", e)

    # File saving
    if files:
        pending_dir = os.path.join(UPLOAD_BASE_DIR, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        pending_files_map = {}

        for doc_key, file in zip(doc_types, files):
            if not file.filename:
                continue

            safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
            pending_path = os.path.join(
                pending_dir, f"{check_id}_{doc_key}_{safe_filename}"
            )

            with open(pending_path, "wb") as f:
                content = await file.read()
                f.write(content)

            pending_files_map[doc_key] = pending_path

        await app.state.collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"documents.pendingFiles": pending_files_map}}
        )

    return {
        "message": "Request queued successfully",
        "check_id": check_id,
        "status": "QUEUED"
    }

# ---------------- CHECK STATUS API ----------------

@app.get("/check-status/{check_id}")
async def get_status(check_id: str):
    try:
        oid = ObjectId(check_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    record = await app.state.collection.find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Not found")

    return serialize_doc(record)

# ---------------- LIST ALL CANDIDATES ----------------

@app.get("/candidates")
async def list_candidates():
    candidates_cursor = app.state.collection.find({})
    candidates = []
    async for doc in candidates_cursor:
        candidates.append(serialize_doc(doc))
    return {"candidates": candidates}
