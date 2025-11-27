# worker.py

import os
import asyncio
import json
import re
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bson import ObjectId

# --- Local Application Imports ---
from azure_client import get_azure_client, get_azure_deployment
from llm_parser import parse_single_doc_with_vision
from utils import save_local_payload, merge_vision_into_structured
from email_utils import send_mail
# ----------------------------- Worker Configuration -----------------------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "mydb")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "employees")
AZURE_PROFILE = "4O"

# ----------------------------- Core Worker Logic -----------------------------
async def process_single_job(db_collection, job):
    check_id_str = str(job["_id"])
    print(f"[{check_id_str}] Found job. Locking and processing...")

    await db_collection.update_one(
        {"_id": job["_id"]},
        {"$set": {"status": "PROCESSING", "updatedAt": datetime.now(timezone.utc)}}
    )

    try:
        client = get_azure_client(AZURE_PROFILE)
        deployment = get_azure_deployment(AZURE_PROFILE)
    except Exception as e:
        print(f"[{check_id_str}] Azure config error: {e}")
        await db_collection.update_one(
            {"_id": job["_id"]},
            {"$set": {"status": "FAILED", "error_message": str(e)}}
        )
        return

    pending_files = job.get("documents", {}).get("pendingFiles", {})
    if not pending_files:
        print(f"[{check_id_str}] No pending files found. Marking as complete.")
        await db_collection.update_one(
            {"_id": job["_id"]},
            {"$set": {"status": "COMPLETED"}}
        )
        return

    vision_results = {}
    saved_file_infos = {}

    for doc_key, pending_path in pending_files.items():
        try:
            filename = os.path.basename(pending_path).split("_", 2)[-1]
            with open(pending_path, "rb") as f:
                content = f.read()

            parsed = parse_single_doc_with_vision(
                client, deployment, content, filename=filename, doc_key=doc_key,
            )
            vision_results[doc_key] = parsed or {}
            permanent_path = save_local_payload(doc_key, filename, content, parsed or {})

            if doc_key not in saved_file_infos:
                saved_file_infos[doc_key] = []
            saved_file_infos[doc_key].append(
                {"fileName": filename, "filePath": permanent_path}
            )
            os.remove(pending_path)
        except Exception as e:
            print(f"[{check_id_str}] Failed to process file {pending_path}: {e}")
            continue

    set_payload = {}
    
    # 2. Call merge_vision, which will populate 'set_payload' with dot-notation keys.
    merge_vision_into_structured(
        set_payload,
        vision_results,
        job.get("metadata", {})
    )

    # 3. Manually add the saved file paths using dot notation.
    for doc_key, file_infos in saved_file_infos.items():
        if doc_key in ("relievingLetter", "salarySlips", "otherCertificates"):
            set_payload[f"documents.{doc_key}"] = file_infos
        else:
            if file_infos:
                set_payload[f"documents.{doc_key}"] = file_infos[0]
    
    # 4. Add the final status and timestamp to the payload.
    set_payload["status"] = "COMPLETED"
    set_payload["updatedAt"] = datetime.now(timezone.utc)
    
    # 5. Perform the final, non-conflicting update.
    await db_collection.update_one(
        {"_id": job["_id"]},
        {
            "$set": set_payload,
            "$unset": {"documents.pendingFiles": ""}, # This no longer conflicts
        },
    )
    print(f"[{check_id_str}] Job finished successfully.")

    # 6. Send verification email to previous HR (if email present)
    metadata = job.get("metadata", {}) or {}
    previous_hr_email = metadata.get("previousHrEmail")

    if previous_hr_email:
        candidate_name = metadata.get("candidateName") or "the candidate"
        employer = metadata.get("employer") or "your ex-employee"

        subject = f"Employment verification for {candidate_name}"
        body = f"""Dear Sir/Madam,

        We are conducting a background verification for {candidate_name}, who has mentioned
        previous employment at your organization ({employer}).

        Kindly confirm the following details at your convenience:
        - Employment period
        - Designation
        - Last drawn CTC (optional)
        - Any performance or conduct issues (if applicable)

        You may reply directly to this email with your confirmation.

        Thanks and regards,
        Background Verification Team
        """

        try:
            # smtplib is blocking – run it in a thread so we don't block the event loop
            await asyncio.to_thread(
                send_mail,
                previous_hr_email,
                subject,
                body,
            )

            await db_collection.update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "verification.previousHrEmailSent": True,
                        "verification.previousHrEmailSentAt": datetime.now(timezone.utc),
                    }
                },
            )
            print(f"[{check_id_str}] Verification email sent to {previous_hr_email}")
        except Exception as e:
            # Log failure in Mongo so we can retry later if needed
            await db_collection.update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "verification.previousHrEmailSent": False,
                        "verification.previousHrEmailError": str(e),
                        "verification.previousHrEmailSentAt": datetime.now(timezone.utc),
                    }
                },
            )
            print(f"[{check_id_str}] Failed to send verification email: {e}")


async def main():
    """The main function for the worker process."""
    print("Worker starting...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    collection = db[MONGODB_COLLECTION]
    job = await collection.find_one({"status": "QUEUED"})
    if job:
        await process_single_job(collection, job)
    else:
        print("No queued jobs found.")
    client.close()
    print("Worker finished.")

# ----------------------------- Script Entry Point -----------------------------
if __name__ == "__main__":
    asyncio.run(main())