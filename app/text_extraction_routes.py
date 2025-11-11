"""
Consolidated text extraction routes under app/ to simplify structure.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from app.utils.text_extraction import extract_text_from_image
from app.utils.tools import process_pdf_with_tool
from app.schemas.text_extraction import ExtractedTextDict


router = APIRouter()

@router.post("/extract-text", response_model=ExtractedTextDict)
async def extract_text(file: UploadFile = File(...)):
    """Extract text from image or PDF using tool-based approach."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ""
    
    try:
        if file_extension in ["png", "jpg", "jpeg"]:
            # Process as image
            extracted_text = extract_text_from_image(file_bytes)
        elif file_extension == "pdf":
            # Process as PDF using tool
            extracted_text = process_pdf_with_tool(file_bytes, file.filename)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an image or PDF file.")

        if not extracted_text or not isinstance(extracted_text, dict) or len(extracted_text) == 0:
            raise HTTPException(status_code=500, detail="Text extraction failed - no text was extracted")

        return JSONResponse(
            status_code=200,
            content={"status": True, "extracted_text": extracted_text},
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error during text extraction: {str(exc)}")