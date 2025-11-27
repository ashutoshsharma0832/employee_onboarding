import os
import io
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from bson import ObjectId
from fastapi import HTTPException
from pypdf import PdfReader

# ----------------------------- Global Config -----------------------------
UPLOAD_BASE_DIR = os.getenv("UPLOAD_BASE_DIR", "./uploads")

# ----------------------------- DB Utilities -----------------------------
def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    return doc

def serialize_docs(docs: List[dict]) -> List[dict]:
    """Serializes a list of documents, converting ObjectId to string."""
    return [serialize_doc(doc) for doc in docs]

# ----------------------------- File & Directory Utilities -----------------------------


def save_local_payload(doc_key: str, filename: str, raw_bytes: bytes, parsed_result: dict) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_doc_key = doc_key.replace("/", "_")
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    folder = os.path.join(UPLOAD_BASE_DIR, safe_doc_key)
    ensure_dir(folder)
    base_filename = f"{ts}_{safe_filename}"
    file_path = os.path.join(folder, base_filename)
    json_path = file_path + ".json"
    with open(file_path, "wb") as f:
        f.write(raw_bytes)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(parsed_result, f, ensure_ascii=False, indent=2)
    return os.path.join(safe_doc_key, base_filename)

# ----------------------------- Data Processing Utilities -----------------------------
def _to_float(x):
    try: return float(str(x).strip())
    except (ValueError, TypeError): return None

def normalize_date(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = s.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try: return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception: pass
    return s

def merge_vision_into_structured(
    final_payload: Dict[str, Any],
    vision_results: Dict[str, Any],
    existing_metadata: Dict[str, Any]
) -> None:
    """
    Merges structured data from Vision API results into the final payload.

    IMPORTANT: This version only writes MongoDB dot-notation keys
    (e.g. "documents.tenthResult") so it can be safely combined with other
    "documents.<field>" updates in a single $set.
    """

    # We'll put all raw vision outputs under documents.rawVisionOutput
    raw_output_dict: Dict[str, Any] = {}

    for doc_key, vr in (vision_results or {}).items():
        vr = vr or {}
        raw_output_dict[doc_key] = vr

        ex = vr.get("extracted") or {}
        if not ex:
            continue

        # ----- 10th marksheet → documents.tenthResult -----
        if doc_key == "tenthMarksheet":
            cg = _to_float(ex.get("cgpa") or ex.get("CGPA"))
            percentage = _to_float(ex.get("percentage"))
            marks_obt = _to_float(ex.get("total") or ex.get("marksObtained"))
            max_marks = _to_float(ex.get("max_total") or ex.get("maxMarks"))

            # Backfill percentage if needed
            if percentage is None:
                if marks_obt is not None and max_marks and max_marks > 0:
                    try:
                        percentage = round((marks_obt / max_marks) * 100.0, 2)
                    except Exception:
                        pass
                elif cg is not None and 0 < cg <= 10:
                    percentage = round(cg * 9.5, 2)

            final_payload["documents.tenthResult"] = {
                "marksObtained": marks_obt,
                "maxMarks": max_marks,
                "cgpa": cg,
                "percentage": percentage,
                "board": ex.get("board_name") or ex.get("board"),
            }

        # ----- Aadhaar / domicile → documents.aadhaarDetails -----
        if doc_key == "aadhaarOrDomicile":
            raw_num = ex.get("aadhaar_number") or ex.get("aadhaarNumber")
            aadhaar = re.sub(r"\D", "", raw_num) if raw_num else None

            final_payload["documents.aadhaarDetails"] = {
                "aadhaarNumber": aadhaar or None,
                "dateOfBirth": normalize_date(
                    ex.get("date_of_birth") or ex.get("dob") or ex.get("dateOfBirth")
                ),
                "gender": ex.get("gender") or None,
            }

        # ----- Try to fill candidateName if missing -----
        candidate_name = ex.get("student_full_name") or ex.get("candidate_name")
        if candidate_name and not existing_metadata.get("candidateName"):
            final_payload["metadata.candidateName"] = candidate_name

    # Only set rawVisionOutput if we actually have something
    if raw_output_dict:
        final_payload["documents.rawVisionOutput"] = raw_output_dict



# ===================== PDF & Text Utils =====================

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        texts = [page.extract_text() or "" for page in reader.pages]
        raw = "\n".join(texts)
        return re.sub(r"[ \t]+", " ", raw).strip()
    except Exception:
        # Handle cases where PyPDF2 might fail on a corrupted file
        return ""

def safe_trim(text: str, max_chars: int = 12000) -> str:
    """Safely trims text to a maximum length without breaking words."""
    if len(text) <= max_chars:
        return text
    # Trim at a word boundary
    trimmed_text = text[:max_chars]
    last_space = trimmed_text.rfind(' ')
    if last_space != -1:
        return trimmed_text[:last_space] + "\n...[TRIMMED]"
    return trimmed_text + "\n...[TRIMMED]"


# ----------------------------- Utilities -----------------------------
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)