"""
Pydantic schemas for text extraction output.
"""

from typing import Dict, Union
from pydantic import BaseModel, Field, field_validator

class ExtractedTextDict(BaseModel):
    status: bool | None = Field(
        description="Status of the text extraction"
    )
    extracted_text: Dict[str, str] = Field(
        description="Extracted text organized by question numbers"
    )
    s3_key: str | None = Field(
        description="S3 key where the original file is stored"
    )

    @field_validator('extracted_text')
    @classmethod
    def validate_extracted_text(cls, v: Dict[str, str]):
        if not isinstance(v, dict):
            raise ValueError("extracted_text must be a dictionary")
        if not v:
            raise ValueError("extracted_text cannot be empty")
        return v
