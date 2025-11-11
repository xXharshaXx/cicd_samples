"""
Configuration settings for the Text Extraction API.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Gemini API Configuration
    #GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY: str = "AIzaSyDVsaQfoTghPu8q369JjwbFEKsItucY1rA"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    MAX_OUTPUT_TOKENS: int = 4096  
    TEMPERATURE: float = 0.01  
    TOP_P: float = 0.9  
    
    # Text extraction settings
    MAX_RETRIES: int = 3  
    TIMEOUT_SECONDS: int = 60  
    MIN_TEXT_LENGTH: int = 10  

    LANGFUSE_SECRET_KEY: str = "sk-lf-78ca7470-57cd-4506-a45a-0e94d727e37e"
    LANGFUSE_PUBLIC_KEY: str = "pk-lf-0f01f8b2-f0b7-4251-a301-bceab943ceb3"
    LANGFUSE_HOST="http://95.216.201.95:3000"

    current_env: str = "dev"

settings = Settings()
