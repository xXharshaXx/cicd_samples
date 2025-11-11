"""
LangChain tools for text extraction.
"""
from typing import Dict
import fitz  # PyMuPDF
from PIL import Image
import io
import logging
from datetime import datetime
from app.utils.text_extraction import extract_text_from_image, _normalize_image_size

# Get logger from text_extraction
logger = logging.getLogger("text_extraction")

def _ts() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")

def _pil_image_from_pixmap(pix: "fitz.Pixmap") -> Image.Image:
    """Convert PyMuPDF pixmap to PIL Image."""
    if pix.alpha:  # remove alpha for consistency
        pix = fitz.Pixmap(fitz.csRGB, pix)
    img_bytes = pix.tobytes("png")
    return Image.open(io.BytesIO(img_bytes))


def pdf_to_combined_image_tool(pdf_bytes: bytes, dpi: int = 300) -> bytes:
    """
    Convert PDF to a single combined image (all pages).
    Returns image bytes for processing.
    """

    doc = None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Create a single large image from all pages
        all_pages = []
        total_height = 0
        max_width = 0
        
        # First pass: calculate dimensions and collect pages
        for page in doc:
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pil_image = _pil_image_from_pixmap(pix)
            # Normalize each page to a consistent width to control final size
            target_page_width = 1600
            if pil_image.width != target_page_width and pil_image.width > 0:
                scale = target_page_width / float(pil_image.width)
                new_w = target_page_width
                new_h = int(round(pil_image.height * scale))
                pil_image = pil_image.resize((max(new_w, 1), max(new_h, 1)), Image.LANCZOS)
            all_pages.append(pil_image)
            total_height += pil_image.height
            max_width = max(max_width, pil_image.width)
        
        # Create a single large image
        combined_image = Image.new('RGB', (max_width, total_height), 'white')
        y_offset = 0
        
        # Second pass: paste all pages into the combined image
        for pil_image in all_pages:
            combined_image.paste(pil_image, (0, y_offset))
            y_offset += pil_image.height
        
        # Final safety normalization on the combined image
        combined_image = _normalize_image_size(combined_image)

        # Convert to bytes
        buf = io.BytesIO()
        combined_image.save(buf, format="PNG")
        return buf.getvalue()
        
    except Exception as e:
        logger.error(f"PDF processing error: {e}")
        return b""
    finally:
        try:
            if doc is not None:
                doc.close()
        except Exception:
            pass


def process_pdf_with_tool(pdf_bytes: bytes, filename: str = "unknown") -> Dict[str, str]:
    """
    Process PDF using tool-based approach.
    Tool converts PDF to combined image, then uses standard image extraction.
    """
    logger.info(f"Starting PDF processing with tool for file: {filename}")
    
    # Tool converts PDF to combined image
    image_bytes = pdf_to_combined_image_tool(pdf_bytes)
    
    if not image_bytes:
        logger.error("PDF to image conversion failed")
        return {}
    
    logger.info("PDF converted to image, now extracting text")
    # Use standard image extraction
    result = extract_text_from_image(image_bytes)
    
    logger.info(f"PDF extraction {'success' if result else 'failed'}")
    return result