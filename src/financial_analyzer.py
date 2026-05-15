import requests
import json
import os
import re
from datetime import date
from dotenv import load_dotenv
from config.settings import DATA_OUTPUT, OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL

load_dotenv()

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/porter-moat-analyzer",
}

ANALYSIS_PROMPT = """You are a senior equity analyst with expertise in competitive strategy and valuation.

Analyze the following company as a potential long-term investment. Be rigorous, specific, and honest.

═══════════════════════════════════════════
COMPANY: {company} ({ticker})
Sector: {sector} | Industry: {industry}
═══════════════════════════════════════════

── PORTER'S FIVE FORCES (from 10-K analysis) ──
Moat Score: {moat_score}/5
{porter_details}

── FINANCIAL HISTORY ({years} years) ──
Revenue CAGR: {cagr}%

Year | Revenue | Gross% | Op% | Net% | FCF% | ROIC% | D/E
{financial_table}

── CURRENT VALUATION ──
Price: ${price}
P/E: {pe} | Forward P/E: {fpe}
EV/EBITDA: {evebitda}
PEG Ratio: {peg} (P/E ÷ Revenue CAGR — <1 cheap, >2 expensive)
% from 52w High: {pct_high}%
Market Cap: ${mktcap}B
Dividend Yield: {div_yield}

── KEY SIGNALS TO EVALUATE ──
1. Does the moat score match the financial data? (high moat = stable/growing margins)
2. Is ROIC persistently above 15%? (Buffett's threshold for a real moat)
3. Is the valuation reasonable given the growth rate?
4. Are margins improving, stable, or deteriorating?
5. Is the debt level sustainable?

══════════════════════════════════════════════════════
Respond ONLY with a valid JSON object, no markdown fences, no preamble:
{{
  "ticker": "{ticker}",
  "company": "{company}",
  "investment_score": <1-10 where 10 = strongest buy>,
  "verdict": "<one of: strong buy / buy / hold / avoid / strong avoid>",
  "moat_confirmed_by_numbers": <true or false>,
  "valuation_assessment": "<one of: very cheap / cheap / fair / expensive / very expensive>",
  "margin_trend": "<one of: strongly improving / improving / stable / deteriorating / strongly deteriorating>",
  "roic_assessment": "<one of: exceptional (>25%) / strong (15-25%) / adequate (10-15%) / weak (<10%)>",
  "key_thesis": "<3-4 sentences explaining the core investment case FOR or AGAINST>",
  "moat_vs_numbers": "<2-3 sentences on whether Porter analysis is confirmed or contradicted by the financials>",
  "upside_catalysts": ["<specific catalyst 1>", "<specific catalyst 2>", "<specific catalyst 3>"],
  "downside_risks": ["<specific risk 1>", "<specific risk 2>", "<specific risk 3>"],
  "valuation_notes": "<2 sentences on current price vs intrinsic value — mention PEG and EV/EBITDA>",
  "comparable_companies": ["<ticker of similar company>", "<ticker of similar company>"],
  "time_horizon": "<one of: short-term (<1yr) / medium-term (1-3yr) / long-term (3yr+)>",
  "analysis_date": "{today}"
}}
"""

def build_porter_details(porter: dict) -> str:
    forces = porter.get("forces", {})
    lines = []
    labels = {
        "rivalry": "Rivalry among competitors",
        "new_entrants": "Threat of new entrants",
        "substitutes": "Threat of substitutes",
        "buyer_power": "Bargaining power of buyers",
        "supplier_power": "Bargaining power of suppliers",
    }
    for key, label in labels.items():
        f = forces.get(key, {})
        score = f.get("score", "?")
        rationale = f.get("rationale", "")[:120]
        lines.append(f"  {label}: {score}/5 — {rationale}")
    risks = porter.get("key_risks", [])
    if risks:
        lines.append(f"\nKey risks from 10-K: {' | '.join(risks[:3])}")
    return "\n".join(lines)

def build_financial_table(history: list) -> str:
    lines = []
    for h in history:
        lines.append(
            f"{h['year']} | "
            f"${h['revenue_B']}B | "
            f"{h.get('gross_margin') or '-'}% | "
            f"{h.get('operating_margin') or '-'}% | "
            f"{h.get('net_margin') or '-'}% | "
            f"{h.get('fcf_margin') or '-'}% | "
            f"{h.get('roic') or '-'}% | "
            f"{h.get('debt_equity') or '-'}"
        )
    return "\n".join(lines)

def compute_peg(pe, cagr) -> str:
    try:
        if pe and cagr and float(cagr) > 0:
            return str(round(float(pe) / float(cagr), 2))
    except:
        pass
    return "n/a"

def call_llm(prompt: str) -> str | None:
    try:
        r = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=HEADERS,
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a financial analyst API. Respond only with valid JSON. No markdown, no explanation, no code fences."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.1,
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  LLM error: {e}")
        return None

def parse_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None

def analyze(ticker: str) -> dict | None:
    cache_path = f"{DATA_OUTPUT}/{ticker}_investment.json"
    if os.path.exists(cache_path):
        print(f"{ticker}: caricato da cache")
        with open(cache_path) as f:
            return json.load(f)

    # Carica dati Porter
    porter_path = f"{DATA_OUTPUT}/{ticker}_porter.json"
    fin_path    = f"{DATA_OUTPUT}/{ticker}_financials.json"

    if not os.path.exists(porter_path):
        print(f"{ticker}: analisi Porter mancante — esegui analyzer.py prima")
        return None
    if not os.path.exists(fin_path):
        print(f"{ticker}: dati finanziari mancanti — esegui financials.py prima")
        return None

    with open(porter_path) as f:
        porter = json.load(f)
    with open(fin_path) as f:
        fin = json.load(f)

    c = fin.get("current", {})
    history = fin.get("history", [])
    cagr = fin.get("revenue_cagr")

    prompt = ANALYSIS_PROMPT.format(
        ticker=ticker,
        company=porter.get("company", ticker),
        sector=c.get("sector", "Unknown"),
        industry=c.get("industry", "Unknown"),
        moat_score=porter.get("moat_score", "?"),
        porter_details=build_porter_details(porter),
        years=len(history),
        cagr=cagr,
        financial_table=build_financial_table(history),
        price=c.get("price", "?"),
        pe=round(c.get("pe_ratio"), 1) if c.get("pe_ratio") else "n/a",
        fpe=round(c.get("forward_pe"), 1) if c.get("forward_pe") else "n/a",
        evebitda=c.get("ev_ebitda", "n/a"),
        peg=compute_peg(c.get("pe_ratio"), cagr),
        pct_high=c.get("pct_from_52w_high", "n/a"),
        mktcap=c.get("market_cap_B", "n/a"),
        div_yield=round(c.get("dividend_yield", 0) * 100, 2) if c.get("dividend_yield") else "0",
        today=str(date.today()),
    )

    print(f"{ticker}: chiamata LLM per analisi integrata...")
    raw = call_llm(prompt)
    if not raw:
        print(f"{ticker}: LLM non ha risposto")
        return None

    result = parse_json(raw)
    if not result:
        print(f"{ticker}: JSON parsing fallito")
        result = {"ticker": ticker, "error": "parse_failed", "raw": raw}

    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"{ticker}: analisi salvata — score: {result.get('investment_score')}/10 | {result.get('verdict')}")
    return result

def print_analysis(ticker: str):
    path = f"{DATA_OUTPUT}/{ticker}_investment.json"
    if not os.path.exists(path):
        print(f"{ticker}: nessuna analisi trovata")
        return
    with open(path) as f:
        d = json.load(f)
    if "error" in d:
        print(f"{ticker}: errore — {d['error']}")
        return

    verdict_colors = {
        "strong buy": "🟢", "buy": "🟩",
        "hold": "🟡", "avoid": "🟠", "strong avoid": "🔴"
    }
    icon = verdict_colors.get(d.get("verdict", ""), "⚪")

    print(f"\n{'='*65}")
    print(f"{icon}  {d['ticker']} — {d['company']}")
    print(f"{'='*65}")
    print(f"  Investment score:  {d.get('investment_score')}/10")
    print(f"  Verdict:           {d.get('verdict', '').upper()}")
    print(f"  Valuation:         {d.get('valuation_assessment')}")
    print(f"  Margin trend:      {d.get('margin_trend')}")
    print(f"  ROIC:              {d.get('roic_assessment')}")
    print(f"  Moat confirmed:    {'Yes ✓' if d.get('moat_confirmed_by_numbers') else 'No ✗'}")
    print(f"  Time horizon:      {d.get('time_horizon')}")
    print(f"\n  Thesis:")
    print(f"    {d.get('key_thesis', '')}")
    print(f"\n  Moat vs numbers:")
    print(f"    {d.get('moat_vs_numbers', '')}")
    print(f"\n  Upside catalysts:")
    for c in d.get("upside_catalysts", []):
        print(f"    ↑ {c}")
    print(f"\n  Downside risks:")
    for r in d.get("downside_risks", []):
        print(f"    ↓ {r}")
    print(f"\n  Valuation notes:")
    print(f"    {d.get('valuation_notes', '')}")
    print(f"\n  Comparable companies: {', '.join(d.get('comparable_companies', []))}")

if __name__ == "__main__":
    tickers = [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corporation"),
        ("GOOGL", "Alphabet Inc."),
    ]
    for ticker, _ in tickers:
        analyze(ticker)
        print_analysis(ticker)
