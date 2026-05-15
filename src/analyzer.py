import os
import json
import re
import requests
import time
from datetime import date
from config.settings import (
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL,
    DATA_PROCESSED, DATA_OUTPUT
)

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/porter-moat-analyzer",
}

PORTER_PROMPT = """You are an expert financial analyst specializing in competitive strategy.

Analyze the following company using Porter's Five Forces framework.
Company: {company} ({ticker})

TEXT FROM 10-K:
{text}

If the text above does not contain enough information for a full analysis, use your knowledge of this company to supplement, but clearly flag what is inferred vs. from the document.

Respond ONLY with a valid JSON object, no markdown, no preamble:
{{
  "ticker": "{ticker}",
  "company": "{company}",
  "forces": {{
    "rivalry": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "new_entrants": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "substitutes": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "buyer_power": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "supplier_power": {{"score": <1-5>, "rationale": "<2-3 sentences>"}}
  }},
  "moat_score": <weighted average 1-5>,
  "moat_summary": "<3-4 sentences summarizing the competitive position>",
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "data_source": "10-K" 
}}

Scoring: HIGH score = FAVORABLE for the company.
rivalry=5 means very little competition.
new_entrants=5 means very high barriers to entry.
substitutes=5 means no credible substitutes.
buyer_power=5 means buyers have no pricing power over the company.
supplier_power=5 means suppliers have no pricing power over the company.
"""

FALLBACK_PROMPT = """You are an expert financial analyst.

The text extraction from the 10-K filing for {company} ({ticker}) did not yield clean section data.
Here is the raw extracted text (may be incomplete):

{text}

Based on this text AND your knowledge of {company}, perform a Porter's Five Forces analysis.
Clearly note in the rationale what comes from the document vs. your prior knowledge.

Respond ONLY with a valid JSON object, no markdown, no preamble:
{{
  "ticker": "{ticker}",
  "company": "{company}",
  "forces": {{
    "rivalry": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "new_entrants": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "substitutes": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "buyer_power": {{"score": <1-5>, "rationale": "<2-3 sentences>"}},
    "supplier_power": {{"score": <1-5>, "rationale": "<2-3 sentences>"}}
  }},
  "moat_score": <weighted average 1-5>,
  "moat_summary": "<3-4 sentences>",
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "data_source": "fallback+prior_knowledge"
}}
"""

def call_llm(prompt: str, max_retries: int = 3) -> str | None:
    """Chiama OpenRouter con retry automatico."""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=HEADERS,
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.1,
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
    return None

def parse_json_response(raw: str) -> dict | None:
    """Estrae JSON dalla risposta anche se contiene testo extra."""
    # Prova parsing diretto
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Cerca blocco JSON nella risposta
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None

def is_good_extraction(text: str) -> bool:
    """Verifica che il testo estratto contenga contenuto narrativo utile."""
    keywords = ["competition", "market", "business", "revenue", "customers",
                "products", "services", "risk", "competitive"]
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return hits >= 3 and len(text) > 2000

def analyze_company(ticker: str, company_name: str) -> dict | None:
    """Analisi Porter completa con fallback automatico."""
    os.makedirs(DATA_OUTPUT, exist_ok=True)
    cache_path = f"{DATA_OUTPUT}/{ticker}_porter.json"

    if os.path.exists(cache_path):
        print(f"{ticker}: caricato da cache")
        with open(cache_path) as f:
            return json.load(f)

    # Carica testo estratto
    qual_path = f"{DATA_PROCESSED}/{ticker}_qualitative.txt"
    if not os.path.exists(qual_path):
        print(f"{ticker}: testo qualitativo non trovato")
        return None

    with open(qual_path) as f:
        text = f.read()

    # Scegli prompt in base alla qualità dell'estrazione
    if is_good_extraction(text):
        print(f"{ticker}: estrazione OK, uso prompt standard")
        prompt = PORTER_PROMPT.format(
            company=company_name, ticker=ticker, text=text[:35000]
        )
        data_source = "10-K"
    else:
        print(f"{ticker}: estrazione scarsa, uso fallback prompt")
        prompt = FALLBACK_PROMPT.format(
            company=company_name, ticker=ticker, text=text[:35000]
        )
        data_source = "fallback"

    print(f"{ticker}: chiamata LLM...")
    raw = call_llm(prompt)

    if not raw:
        print(f"{ticker}: LLM non ha risposto")
        return None

    result = parse_json_response(raw)

    if not result:
        print(f"{ticker}: parsing JSON fallito, salvo raw")
        result = {
            "ticker": ticker,
            "company": company_name,
            "error": "json_parse_failed",
            "raw": raw,
            "data_source": data_source
        }

    result["analysis_date"] = str(date.today())

    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"{ticker}: analisi salvata")
    return result

if __name__ == "__main__":
    test_companies = [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corporation"),
        ("GOOGL", "Alphabet Inc."),
    ]
    for ticker, company in test_companies:
        print(f"\n{'='*50}")
        result = analyze_company(ticker, company)
        if result and "forces" in result:
            print(f"Moat score: {result.get('moat_score')}")
            print(f"Summary: {result.get('moat_summary', '')[:200]}")
        elif result and "error" in result:
            print(f"Errore: {result['error']}")
