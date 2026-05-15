import re
import os
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from config.settings import DATA_RAW, DATA_PROCESSED

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

MAX_CHARS = 40000

SECTION_PATTERNS = {
    "item1":  r"item\s*1[\.\s]+\s{2,}business",
    "item1a": r"item\s*1a[\.\s]+\s{2,}risk\s*factors",
    "item3":  r"item\s*3[\.\s]+\s{2,}legal\s*proceedings",
    "item7":  r"item\s*7[\.\s]+\s{2,}management",
    "item8":  r"item\s*8[\.\s]+\s{2,}financial\s*statements",
}

QUALITATIVE_SECTIONS = ["item1", "item1a", "item3"]
FINANCIAL_SECTIONS   = ["item7", "item8"]

def parse_text(raw: str) -> str:
    """Prova prima lxml (HTML), poi lxml-xml se fallisce."""
    if "<html" in raw.lower() or "<body" in raw.lower():
        # Usa HTML parser — funziona anche con iXBRL
        soup = BeautifulSoup(raw, "lxml")
        # Rimuovi tag script e style
        for tag in soup(["script", "style", "ix:header", "ix:nonnumeric"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    return raw

def find_section_start(text_lower: str, pattern: str) -> int | None:
    m = re.search(pattern, text_lower)
    return m.start() if m else None

def extract_sections(text: str, section_keys: list[str]) -> str:
    text_lower = text.lower()

    all_positions = {}
    for key, pattern in SECTION_PATTERNS.items():
        pos = find_section_start(text_lower, pattern)
        if pos is not None:
            all_positions[key] = pos

    sorted_positions = sorted(all_positions.items(), key=lambda x: x[1])
    pos_list = [p for _, p in sorted_positions]

    chunks = []
    total = 0

    for key in section_keys:
        if key not in all_positions:
            continue
        start = all_positions[key]
        next_starts = [p for p in pos_list if p > start]
        end = next_starts[0] if next_starts else start + MAX_CHARS
        end = min(end, start + MAX_CHARS)
        chunk = text[start:end].strip()
        chunks.append(chunk)
        total += len(chunk)
        if total >= MAX_CHARS:
            break

    return "\n\n---\n\n".join(chunks)

def process_ticker(ticker: str) -> dict | None:
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    raw_path = f"{DATA_RAW}/{ticker}_10k.txt"

    if not os.path.exists(raw_path):
        print(f"{ticker}: 10-K non trovato")
        return None

    with open(raw_path) as f:
        raw = f.read()

    text = parse_text(raw)
    results = {}

    for label, keys in [("qualitative", QUALITATIVE_SECTIONS), ("financial", FINANCIAL_SECTIONS)]:
        out_path = f"{DATA_PROCESSED}/{ticker}_{label}.txt"
        if os.path.exists(out_path):
            print(f"{ticker} {label}: caricato da cache")
            with open(out_path) as f:
                results[label] = f.read()
            continue

        extracted = extract_sections(text, keys)
        if not extracted:
            print(f"{ticker} {label}: sezioni non trovate")
            extracted = text[:MAX_CHARS]

        with open(out_path, "w") as f:
            f.write(extracted)
        print(f"{ticker} {label}: {len(extracted):,} caratteri salvati")
        results[label] = extracted

    return results

if __name__ == "__main__":
    for ticker in ["AAPL", "MSFT", "GOOGL"]:
        print(f"\n{'='*50}")
        print(f"Processing {ticker}...")
        results = process_ticker(ticker)
        if results:
            for label, text in results.items():
                print(f"\n--- {ticker} {label.upper()} (primi 400 caratteri) ---")
                print(text[:400])
