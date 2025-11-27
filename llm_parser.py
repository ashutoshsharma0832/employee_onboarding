# llm_parser.py
import json
import re
from typing import Dict, Optional, Any, List

from openai import AzureOpenAI
from schemas import TenthResult, AadhaarDetails  # existing schemas
import fitz  # PyMuPDF, for vision branch
import base64
from io import BytesIO

# ===================== Regex Fallbacks =====================
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\d{10})")

def simple_fallback(texts_merged: str) -> Dict[str, Optional[str]]:
    email = None
    phone = None
    m_email = EMAIL_RE.search(texts_merged)
    if m_email:
        email = m_email.group(0)
    m_phone = PHONE_RE.search(texts_merged.replace(" ", ""))
    if m_phone:
        phone = m_phone.group(0)[-10:]
    return {"email": email, "phoneNumber": phone}

# ===================== TEXT MODE (your old logic) =====================

def build_llm_prompt(doc_chunks: Dict[str, str]) -> list:
    schema = {
        "metadata": {
            "candidateName": "string or null",
            "city": "string or null",
            "localAddress": "string or null",
            "permanentAddress": "string or null",
            "phoneNumber": "string or null",
            "email": "string or null",
            "employer": "string or null",
            "previousHrEmail": "string or null"
        },
        "documents": {
            "tenthResult": TenthResult.model_json_schema(),
            "aadhaarDetails": AadhaarDetails.model_json_schema(),
        }
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert data extraction AI. Your task is to analyze text from various "
                "candidate documents and populate a JSON object based on the provided schema. "
                "Rules:\n"
                "1. Return ONLY a single, valid JSON object. No explanations, no markdown.\n"
                "2. If a value isn't found, use `null` for that field. Do not invent data.\n"
                "3. For `aadhaarNumber`, remove spaces. For `dateOfBirth`, use YYYY-MM-DD format if possible.\n"
                "4. For `tenthResult`, calculate `percentage` if marks are available. If only CGPA is present, use that.\n"
                "5. Identify the educational board (e.g., CBSE, ICSE) if mentioned."
            ),
        },
        {
            "role": "user",
            "content": f"Extract information into this JSON schema:\n{json.dumps(schema, indent=2)}",
        },
    ]

    labeled_blobs = [f"=== START {key} ===\n{text}\n=== END {key} ===" for key, text in doc_chunks.items()]
    messages.append({
        "role": "user",
        "content": "Here are the document texts:\n\n" + "\n\n".join(labeled_blobs),
    })

    return messages

def parse_documents_with_llm(client: AzureOpenAI, deployment_name: str, doc_texts: Dict[str, str]) -> Dict[str, Any]:
    messages = build_llm_prompt(doc_texts)
    try:
        completion = client.chat.completions.create(
            model=deployment_name,
            temperature=0,
            max_tokens=2000,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content.strip()
        parsed_data = json.loads(content)
        return parsed_data
    except Exception as e:
        print(f"LLM parsing failed: {e}. Using simple fallback.")
        merged_text = "\n".join(doc_texts.values())
        fb = simple_fallback(merged_text)
        return {
            "metadata": {
                "candidateName": None, "city": None, "localAddress": None,
                "permanentAddress": None, "phoneNumber": fb.get("phoneNumber"),
                "email": fb.get("email"), "employer": None, "previousHrEmail": None
            },
            "documents": {
                "tenthResult": None,
                "aadhaarDetails": None,
            },
        }

# ===================== VISION MODE (new) =====================

# backend-maintained descriptions per doc type
DOC_DESCRIPTIONS: Dict[str, str] = {
    "tenthMarksheet": "This is a 10th / SSC / CBSE / ICSE marksheet. Extract student full name, father's name if present, roll/admission number, board name, exam year, list of subjects with marks, total, percentage/CGPA.",
    "twelfthMarksheet": "This is a 12th / HSC marksheet. Extract student name, roll number, board, year, stream if visible, subjects with marks, total, percentage.",
    "aadhaarOrDomicile": "This is an Indian ID / Aadhaar / domicile document. Extract name, date of birth, gender, address if visible, Aadhaar number without spaces.",
    "bachelorsDegree": "This is a degree / provisional certificate. Extract candidate name, university name, programme, department, date of issue, registration/enrollment number, class/division.",
    "resume": "This is a resume. Extract candidate name, email, phone number, current employer/org, total experience (if stated), top skills.",
    "salarySlips": "This is a salary / payslip. Extract employee name, employer/org, employee code/id, month/year, gross, total deductions, net pay.",
    "relievingLetter": "This is a relieving/experience letter. Extract employee name, employer, position, joining date, relieving date.",
}

def _pdf_bytes_to_first_page_b64(pdf_bytes: bytes, zoom: float = 2.0) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")

def parse_single_doc_with_vision(
    client: AzureOpenAI,
    deployment_name: str,
    file_bytes: bytes,
    filename: str,
    doc_key: str,
    description_override: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. turn PDF/image → base64 PNG
    if filename.lower().endswith(".pdf"):
        image_b64 = _pdf_bytes_to_first_page_b64(file_bytes)
    else:
        # assume image
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")

    # 2. pick description
    description = description_override or DOC_DESCRIPTIONS.get(
        doc_key,
        f"This is a document of type '{doc_key}'. Extract all useful fields and identifiers mentioned.",
    )

    # 3. build prompt
    prompt = f"""
You are an expert document parser.

Document type: {doc_key}
Description: {description}

Return ONLY JSON. If a field is missing, return it as null.

Suggested top-level shape:
{{
  "doc_type": "{doc_key}",
  "extracted": {{}}
}}
"""

    resp = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {"role": "system", "content": "You extract structured data from images and PDFs."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                        },
                    },
                ],
            },
        ],
        temperature=0,
    )

    content = resp.choices[0].message.content.strip()
    # sometimes model adds ```json
    if content.startswith("```"):
        content = content.strip("`")
        content = content.split("\n", 1)[-1]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"doc_type": doc_key, "raw": content}
