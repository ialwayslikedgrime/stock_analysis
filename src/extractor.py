import re
import os
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from config.settings import DATA_RAW, DATA_PROCESSED

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

MAX_CHARS = 40000

# Pattern flessibili: case-insensitive, spazi variabili, lettere spaziate (B USINESS)
SECTION_PATTERNS = {
    "item1":  r"item\s*1[\.\s]+b[\s]*u[\s]*s[\s]*i[\s]*n[\s]*e[\s]*s[\s]*s",
    "item1a": r"item\s*1a[\.\s]+r[\s]*i[\s]*s[\s]*k\s+f[\s]*a[\s]*c[\s]*t[\s]*o[\s]*r[\s]*s",
    "item3":  r"item\s*3[\.\s]+l[\s]*e[\s]*g[\s]*a[\s]*l\s+p[\s]*r[\s]*o[\s]*c[\s]*e[\s]*e[\s]*d",
    "item7":  r"item\s*7[\.\s]+m[\s]*a[\s]*n[\s]*a[\s]*g[\s]*e[\s]*m[\s]*e[\s]*n[\s]*t",
    "item8":  r"item\s*8[\.\s]+f[\s]*i[\s]*n[\s]*a[\s]*n[\s]*c[\s]*i[\s]*a[\s]*l\s+s[\s]*t[\s]*a[\s]*t",
}

QUALITATIVE_SECTIONS = ["item1", "item1a", "item3"]
FINANCIAL_SECTIONS   = ["item7", "item8"]

def parse_text(raw: str) -> str:
    if "<html" in raw.lower() or "<body" in raw.lower():
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    return raw

def find_section_starts(text_lower: str, pattern: str) -> list[int]:
    return [m.start() for m in re.finditer(pattern, text_lower)]

def extract_sections(text: str, section_keys: list[str]) -> str:
    text_lower = text.lower()

    all_positions = {}
    for key, pattern in SECTION_PATTERNS.items():
        matches = find_section_starts(text_lower, pattern)
        if matches:
            # Prendi la seconda occorrenza se disponibile (prima = indice)
            all_positions[key] = matches[1] if len(matches) > 1 else matches[0]

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
            print(f"{ticker} {label}: sezioni non trovate, uso fallback")
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
