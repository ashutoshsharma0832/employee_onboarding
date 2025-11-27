# render_pdf_or_image.py
import base64
from io import BytesIO
import fitz  # pymupdf
from PIL import Image
import os

def pdf_bytes_to_first_page_base64(pdf_bytes: bytes, zoom: float = 2.0) -> str:
    # open from bytes
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")

def image_bytes_to_base64(image_bytes: bytes) -> str:
    # normalize to PNG
    img = Image.open(BytesIO(image_bytes))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def filebytes_to_azure_image_b64(file_bytes: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return pdf_bytes_to_first_page_base64(file_bytes)
    # else assume it's an image
    return image_bytes_to_base64(file_bytes)
