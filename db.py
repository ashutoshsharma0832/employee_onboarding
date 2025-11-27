# # db.py
# from datetime import datetime, timezone
# from typing import Dict, Any, Optional
# from motor.motor_asyncio import AsyncIOMotorClient
# from schemas import EmployeePayload

# COLLECTION = "employees"

# async def get_db_client() -> AsyncIOMotorClient:
#     """
#     Placeholder for dependency injection of the DB client.
#     In a real app, you might manage this differently (e.g., in `main.py` state).
#     """
#     # This is a simplified approach. In main.py, we'll attach the client to the app state.
#     pass

# async def upsert_employee(db_collection, employee: EmployeePayload) -> Dict[str, Any]:
#     """
#     Inserts or updates an employee record in the database based on email.
#     """
#     now = datetime.now(timezone.utc)
#     body = employee.model_dump(exclude_unset=True) # Don't save empty optional fields

#     if employee.metadata.email:
#         filter_ = {"metadata.email": employee.metadata.email}
#         update = {"$set": {**body, "updatedAt": now}, "$setOnInsert": {"createdAt": now}}
#         result = await db_collection.update_one(filter_, update, upsert=True)
#         if result.upserted_id:
#             oid = result.upserted_id
#             action = "inserted"
#         else:
#             doc = await db_collection.find_one(filter_, {"_id": 1})
#             oid = doc["_id"]
#             action = "updated"
#         return {"status": "ok", "action": action, "id": str(oid)}
#     else:
#         # If no email is provided, always insert a new document
#         body["createdAt"] = now
#         body["updatedAt"] = now
#         result = await db_collection.insert_one(body)
#         return {"status": "ok", "action": "inserted", "id": str(result.inserted_id)}


# db.py
# from datetime import datetime, timezone
# from typing import Dict, Any, Optional
# from motor.motor_asyncio import AsyncIOMotorClient
# from schemas import EmployeePayload

# COLLECTION = "employees"

# async def get_db_client() -> AsyncIOMotorClient:
#     """
#     Placeholder for dependency injection of the DB client.
#     In a real app, you might manage this differently (e.g., in `main.py` state).
#     """
#     # This is a simplified approach. In main.py, we'll attach the client to the app state.
#     pass

# async def upsert_employee(db_collection, employee: EmployeePayload) -> Dict[str, Any]:
#     """
#     Inserts or updates an employee record in the database based on email.
#     """
#     now = datetime.now(timezone.utc)
#     body = employee.model_dump(exclude_unset=True) # Don't save empty optional fields

#     if employee.metadata.email:
#         filter_ = {"metadata.email": employee.metadata.email}
#         update = {"$set": {**body, "updatedAt": now}, "$setOnInsert": {"createdAt": now}}
#         result = await db_collection.update_one(filter_, update, upsert=True)
#         if result.upserted_id:
#             oid = result.upserted_id
#             action = "inserted"
#         else:
#             doc = await db_collection.find_one(filter_, {"_id": 1})
#             oid = doc["_id"]
#             action = "updated"
#         return {"status": "ok", "action": action, "id": str(oid)}
#     else:
#         # If no email is provided, always insert a new document
#         body["createdAt"] = now
#         body["updatedAt"] = now
#         result = await db_collection.insert_one(body)
#         return {"status": "ok", "action": "inserted", "id": str(result.inserted_id)}

# # ====================== HR EMAIL UPDATE FUNCTIONS======================

# async def update_hr_status(db_collection, candidate_email: str, sentiment: str, remark: str):
#     """
#     🔖 BOOKMARK: HR EMAIL STATUS UPDATE
#     This function updates candidate status after HR email is processed.
#     """

#     now = datetime.now(timezone.utc)

#     # Map sentiment to status
#     status = "REJECTED" if sentiment == "NEGATIVE" else "VERIFIED"

#     result = await db_collection.update_one(
#         {"metadata.email": candidate_email},
#         {
#             "$set": {
#                 "hr_status": status,
#                 "hr_remark": remark,
#                 "updatedAt": now
#             }
#         }
#     )

#     return {
#         "matched_count": result.matched_count,
#         "status": status
#     }

###########################new logic

# db.py

from datetime import datetime, timezone
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from schemas import EmployeePayload

COLLECTION = "employees"


# ================= DATABASE CLIENT ====================

async def get_db_client() -> AsyncIOMotorClient:
    """
    Creates MongoDB client
    """
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    return client


# ================= UPSERT EMPLOYEE ====================

async def upsert_employee(db_collection, employee: EmployeePayload) -> Dict[str, Any]:
    """
    Inserts or updates employee based on email
    """
    now = datetime.now(timezone.utc)
    body = employee.model_dump(exclude_unset=True)

    if employee.metadata.email:
        filter_ = {"metadata.email": employee.metadata.email}

        update = {
            "$set": {**body, "updatedAt": now},
            "$setOnInsert": {"createdAt": now}
        }

        result = await db_collection.update_one(filter_, update, upsert=True)

        if result.upserted_id:
            oid = result.upserted_id
            action = "inserted"
        else:
            doc = await db_collection.find_one(filter_, {"_id": 1})
            oid = doc["_id"]
            action = "updated"

        return {"status": "ok", "action": action, "id": str(oid)}
    else:
        body["createdAt"] = now
        body["updatedAt"] = now

        result = await db_collection.insert_one(body)
        return {"status": "ok", "action": "inserted", "id": str(result.inserted_id)}


# ================= HR EMAIL STATUS UPDATE ====================

async def update_hr_status(db_collection, candidate_email: str, sentiment: str, remark: str):
    """
    ✅ Updates BOTH main status and HR status
    """
    now = datetime.now(timezone.utc)

    # Map sentiment → DB status
    if sentiment == "NEGATIVE":
        status = "DISCREPANCY"
    else:
        status = "COMPLETED"

    # Update database
    result = await db_collection.update_one(
        {"metadata.email": candidate_email},
        {
            "$set": {
                "status": status,
                "hr_status": status,
                "hr_remark": remark,
                "updatedAt": now
            }
        }
    )

    if result.matched_count == 0:
        raise Exception("Candidate not found for HR update")

    return {
        "matched_count": result.matched_count,
        "status": status
    }
