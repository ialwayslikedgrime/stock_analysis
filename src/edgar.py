import requests
import os
import time
from config.settings import EDGAR_BASE_URL, EDGAR_HEADERS, DATA_RAW

def get_cik(ticker: str) -> str | None:
    """Recupera il CIK di un ticker da EDGAR."""
    mapping_url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(mapping_url, headers=EDGAR_HEADERS)
    data = r.json()
    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None

def get_latest_10k_url(cik: str) -> str | None:
    """Trova l'URL del 10-K più recente per un dato CIK."""
    url = f"{EDGAR_BASE_URL}/submissions/CIK{cik}.json"
    r = requests.get(url, headers=EDGAR_HEADERS)
    filings = r.json().get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])
    for form, accession, doc in zip(forms, accessions, primary_docs):
        if form == "10-K":
            accession_fmt = accession.replace("-", "")
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_fmt}/{doc}"
    return None

def download_10k_text(ticker: str) -> str | None:
    """Scarica e salva il testo grezzo del 10-K per un ticker."""
    os.makedirs(DATA_RAW, exist_ok=True)
    cache_path = f"{DATA_RAW}/{ticker}_10k.txt"
    if os.path.exists(cache_path):
        print(f"{ticker}: caricato da cache")
        with open(cache_path) as f:
            return f.read()
    cik = get_cik(ticker)
    if not cik:
        print(f"{ticker}: CIK non trovato")
        return None
    url = get_latest_10k_url(cik)
    if not url:
        print(f"{ticker}: 10-K non trovato")
        return None
    print(f"{ticker}: scarico da {url}")
    time.sleep(0.5)  # rispetta rate limit SEC
    r = requests.get(url, headers=EDGAR_HEADERS)
    text = r.text
    with open(cache_path, "w") as f:
        f.write(text)
    return text

if __name__ == "__main__":
    for ticker in ["AAPL", "MSFT", "GOOGL"]:
        text = download_10k_text(ticker)
        if text:
            print(f"{ticker}: {len(text):,} caratteri scaricati\n")
