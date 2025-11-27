# schemas.py

# --- MODIFIED HERE ---
# Import Dict to support older Python versions
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime 
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# ===================== Document Detail Schemas =====================
# (No changes needed for TenthResult or AadhaarDetails)
class TenthResult(BaseModel):
    marksObtained: Optional[float] = Field(None, description="Total marks obtained in 10th grade.")
    maxMarks: Optional[float] = Field(None, description="Maximum possible marks.")
    cgpa: Optional[float] = Field(None, description="CGPA if applicable.")
    percentage: Optional[float] = Field(None, description="Calculated percentage.")
    board: Optional[str] = Field(None, description="Name of the educational board (e.g., CBSE).")

class AadhaarDetails(BaseModel):
    aadhaarNumber: Optional[str] = Field(None, description="Aadhaar card number.")
    dateOfBirth: Optional[str] = Field(None, description="Date of birth from the document.")
    gender: Optional[str] = Field(None, description="Gender (Male/Female/Other).")


# ===================== Core Schemas =====================
class DocumentRef(BaseModel):
    fileName: str = Field(..., min_length=1, description="The original name of the uploaded file.")
    filePath: Optional[str] = Field(None, description="The server-side path where the file is stored.")

class Documents(BaseModel):
    """
    A collection of all possible documents and extracted data associated with an employee.
    Each field is optional with a default value.
    """
    # --- Document References (linking to uploaded files) ---
    tenthMarksheet: Optional[DocumentRef] = None
    twelfthMarksheet: Optional[DocumentRef] = None
    bachelorsDegree: Optional[DocumentRef] = None
    bachelorsResult: Optional[DocumentRef] = None
    mastersDegree: Optional[DocumentRef] = None
    mastersResult: Optional[DocumentRef] = None
    resume: Optional[DocumentRef] = None
    identityProof: Optional[DocumentRef] = None
    policeVerification: Optional[DocumentRef] = None
    aadhaarOrDomicile: Optional[DocumentRef] = None
    bankDetails: Optional[DocumentRef] = None
    
    # --- Lists for documents that can have multiple files ---
    relievingLetter: Optional[List[DocumentRef]] = None
    salarySlips: Optional[List[DocumentRef]] = None
    otherCertificates: List[DocumentRef] = Field(default_factory=list)

    # --- Structured Data (populated by LLM vision parsing) ---
    tenthResult: Optional[TenthResult] = None
    aadhaarDetails: Optional[AadhaarDetails] = None
    
    # --- Raw and Temporary Data Fields ---
    # CORRECT SYNTAX: Use default=None as a keyword argument
    rawVisionOutput: Optional[Dict[str, Any]] = Field(default=None, description="Stores the raw JSON output from the vision model for each document type.")
    pendingFiles: Optional[Dict[str, Any]] = Field(default=None, description="A temporary map of doc_key to its path in the pending folder.")
class Metadata(BaseModel):
    """
    Core metadata about the candidate or employee.
    """
    candidateName: Optional[str] = None
    city: Optional[str] = None
    localAddress: Optional[str] = None
    permanentAddress: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[EmailStr] = None
    employer: Optional[str] = None
    previousHrEmail: Optional[EmailStr] = None

    is_verified: Optional[bool] = Field(
        False,
        description="Indicates if the employee's documents have been verified."
    )

    class Config:
        # If later you add more keys in metadata_json, they won't be dropped
        extra = "allow"

class EmployeePayload(BaseModel):
    """
    The main Pydantic model representing the entire employee record.
    This is used for validation before inserting/updating the database.
    """
    metadata: Metadata
    documents: Documents

    # --- NEW: Add fields for tracking the background job status ---
    status: str = Field(default="PENDING", description="The processing status of the check (e.g., PENDING, QUEUED, PROCESSING, COMPLETED, FAILED)")
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # This allows the model to be created from database objects
        from_attributes = True
