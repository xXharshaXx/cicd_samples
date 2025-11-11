import io
import json
import logging
from datetime import datetime
from typing import Dict
from PIL import Image
import google.generativeai as genai
from app.core.config import settings
import boto3
import os
from langfuse import Langfuse

# Simple logger to single file
_LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "logs.txt"))
logger = logging.getLogger("text_extraction")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    os.makedirs(os.path.dirname(_LOG_FILE), exist_ok=True)
    _fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_fh)

def _ts() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")

langfuse = Langfuse(
  secret_key=settings.LANGFUSE_SECRET_KEY,
  public_key=settings.LANGFUSE_PUBLIC_KEY,
  host=settings.LANGFUSE_HOST
)


def validate_and_fill_question_numbers(extracted_text: Dict[str, str]) -> Dict[str, str]:

    if not extracted_text:
        return extracted_text

    numeric_keys = []
    for k in extracted_text.keys():
        try:
            numeric_keys.append(int(k))
        except (ValueError, TypeError):
            continue

    if not numeric_keys:
        return extracted_text

    min_k = min(numeric_keys)
    max_k = max(numeric_keys)

    complete: Dict[str, str] = {}
    # Always start from 1, fill missing numbers from 1 to max
    for n in range(1, max_k + 1):
        sk = str(n)
        complete[sk] = extracted_text.get(sk, "")

    for k, v in extracted_text.items():
        try:
            int(k)
        except (ValueError, TypeError):
            complete[str(k)] = str(v)

    return complete

def extract_text_from_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Extract text from an image using Gemini AI model.
    Returns structured text organized by question numbers.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    # Save input timestamp (reserved for optional diagnostics)
    _stamp = _ts()

    image_file = io.BytesIO(image_bytes)
    pil_image = Image.open(image_file)
    pil_image = _normalize_image_size(pil_image)

    try:
        fuse_prompt = langfuse.get_prompt("Text_extraction_prompt", label=settings.current_env)
        # Pull separate LaTeX formatting guidelines prompt and inject as variable
        try:
            guidelines_prompt = langfuse.get_prompt("latex_formatting_guidelines")
            guidelines_text = guidelines_prompt.compile(labels={"environment": settings.current_env})
        except Exception as _ge:
            logger.warning(f"latex_formatting_guidelines prompt unavailable or failed to compile: {_ge}")
            guidelines_text = None

        if guidelines_text:
            temp_agent_prompt = fuse_prompt.compile(
                labels={"environment": settings.current_env},
                variables={"latex_formatting_guidelines": guidelines_text}
            )
        else:
            temp_agent_prompt = fuse_prompt.compile(labels={"environment": settings.current_env})

        logger.info("Langfuse prompt fetched and compiled")
    except Exception as _pe:
        logger.error(f"Langfuse prompt error: {_pe}")
        # fallback to static prompt if available
        try:
            from app.utils.prompts import EXTRACTION_PROMPT as _fallback_prompt
            temp_agent_prompt = _fallback_prompt
            logger.info("Using fallback EXTRACTION_PROMPT")
        except Exception as _fe:
            logger.error(f"No fallback prompt available: {_fe}")
            return {}

    logger.info("Calling model.generate_content")
    response = model.generate_content(
        contents=[temp_agent_prompt, pil_image],
        generation_config={
            "temperature": settings.TEMPERATURE,
            "top_p": settings.TOP_P,
            "max_output_tokens": settings.MAX_OUTPUT_TOKENS
        }
    )

    if not response.text:
        logger.warning("Model returned empty text")
        return {}

    # Clean response and parse JSON
    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            raw_text = "\n".join(lines[1:-1]).strip()
    
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            extracted_text = parsed.get("extracted_text", parsed)
            if isinstance(extracted_text, dict):
                # Process text to ensure LaTeX formatting is preserved
                processed_text = {}
                for k, v in extracted_text.items():
                    # Clean and fix LaTeX formatting
                    latex_content = str(v).strip()
                    
                    # Fix common LaTeX formatting issues
                    latex_content = latex_content.replace('\\frac', '\\frac')
                    latex_content = latex_content.replace('\\rightarrow', '\\rightarrow')
                    latex_content = latex_content.replace('\\rightleftharpoons', '\\rightleftharpoons')
                    
                    # Fix nested fraction grouping issues
                    # Example: \frac{1}{\phi \pi \epsilon_0} \frac{Q}{\beta} -> \frac{1}{\phi \pi \epsilon_0} \cdot \frac{Q}{\beta}
                    import re
                    # Add multiplication dot between consecutive fractions
                    latex_content = re.sub(r'(\\frac\{[^}]*\}\{[^}]*\})\s*(\\frac)', r'\1 \\cdot \2', latex_content)
                    
                    # Fix spacing around operators - use string replacement to avoid regex issues
                    latex_content = latex_content.replace(' \\cdot ', ' \\cdot ')
                    latex_content = latex_content.replace('\\cdot ', ' \\cdot ')
                    latex_content = latex_content.replace(' \\cdot', ' \\cdot ')
                    
                    processed_text[str(k)] = latex_content
                
                final = validate_and_fill_question_numbers(processed_text)
                logger.info(f"Extraction success | keys={len(final)} | LaTeX format enabled")
                return final
        return {}
    except json.JSONDecodeError as _je:
        logger.error(f"JSON decode error: {_je}")
        return {}


async def get_s3_client():
    """Get AWS S3 client for file operations."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("aws_key_new"),
        aws_secret_access_key=os.getenv("aws_sec_key_new"),
        region_name=os.getenv("aws_region")
    )




def _normalize_image_size(img: Image.Image) -> Image.Image:

    try:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        min_target_width = 1024
        max_dimension = 12000
        max_total_pixels = 80_000_000  # Keep well under PIL's DecompressionBombWarning default

        width, height = img.size

        # Upscale small images to improve OCR readability
        if width < min_target_width and width > 0:
            scale_up = min_target_width / float(width)
            new_w = int(round(width * scale_up))
            new_h = int(round(height * scale_up))
            img = img.resize((max(new_w, 1), max(new_h, 1)), Image.LANCZOS)
            width, height = img.size

        # Downscale if exceeding safe limits
        scale_factors = []
        if width > max_dimension or height > max_dimension:
            scale_factors.append(max_dimension / float(max(width, height)))
        if width > 0 and height > 0 and (width * height) > max_total_pixels:
            from math import sqrt
            scale_factors.append(sqrt(max_total_pixels / float(width * height)))

        if scale_factors:
            scale_down = min(scale_factors)
            new_w = int(round(width * scale_down))
            new_h = int(round(height * scale_down))
            new_w = max(new_w, 1)
            new_h = max(new_h, 1)
            if new_w != width or new_h != height:
                img = img.resize((new_w, new_h), Image.LANCZOS)

        return img
    except Exception:
        # On any failure, return original image to avoid crashing
        return img

