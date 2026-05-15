import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

PROVIDER = "openrouter"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

EDGAR_BASE_URL = "https://data.sec.gov"
EDGAR_HEADERS = {"User-Agent": "otteneremixtape@gmail.com"}

DATA_RAW = "data/raw"
DATA_PROCESSED = "data/processed"
DATA_OUTPUT = "data/output"
