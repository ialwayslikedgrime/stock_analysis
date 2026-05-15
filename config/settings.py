import os
from dotenv import load_dotenv

load_dotenv()

# Switch: "openrouter" o "anthropic"
PROVIDER = "openrouter"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Modelli
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"  # gratuito

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

EDGAR_BASE_URL = "https://data.sec.gov"
EDGAR_HEADERS = {"User-Agent": "otteneremixtape@gmail.com"}

DATA_RAW = "data/raw"
DATA_PROCESSED = "data/processed"
DATA_OUTPUT = "data/output"
