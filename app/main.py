"""
Main FastAPI application for Text Extraction API using Gemini.
"""
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI
from app.text_extraction_routes import router as text_extraction_router
from fastapi.middleware.cors import CORSMiddleware

import logging
logger = logging.getLogger("uvicorn.error")
    

app = FastAPI(
    title="Text Extraction API",
    description="Simple API for extracting text from images using Gemini-flash-2.0"
)

app.include_router(text_extraction_router, prefix="/extraction", tags=["text-extraction"])

 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, workers=4)
    # uvicorn app.main:app --reload --host localhost --port 5001 --workers 4