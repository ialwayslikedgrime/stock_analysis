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

ANALYSIS_PROMPT = """You are a senior equity analyst at a top-tier investment firm. Real investment decisions involving hundreds of thousands of dollars will be made based on your analysis. Be rigorous, honest, contrarian when warranted. Never default to optimism. Always cite specific numbers.

CRITICAL SCORING PHILOSOPHY:
Scores must be calibrated against the entire universe of publicly listed companies.
- Score 10: once-in-a-decade company. Sole provider of a critical input to a structural megatrend, with compounding advantages and no credible competitor. Extremely rare.
- Score 8-9: genuinely exceptional. Top 5% of all listed companies.
- Score 6-7: above average. Top quartile. Real competitive advantage but limited megatrend or some competitive pressure.
- Score 5: average S&P 500 company. No special structural advantage.
- Score 3-4: below average. Mature market, limited moat, headwinds.
- Score 1-2: structurally impaired. Declining industry, no moat, avoid.
If you score most companies 7+, the ranking becomes useless. Be honest about mediocrity.

The goal: identify companies that will OUTPERFORM the S&P 500 index over 5-10 years.

TWO SEPARATE SCORES — CORE OF THE ANALYSIS:

QUALITY SCORE (price-independent):
"How structurally strong is this company, regardless of today's price?"
This does NOT change with stock price. High Quality = add to watchlist, wait for the right price.
Components: Structural positioning (40%) + Competitive moat (35%) + Financial quality (25%)

OPPORTUNITY SCORE (price-dependent):
"Given today's price, is this a good entry point?"
This DOES change with stock price. Same company: 9 quality but 3 opportunity if price is extreme.
Components: Valuation attractiveness (60%) + Quality Score (40%)

High Quality + High Opportunity = strong buy
High Quality + Low Opportunity = watchlist, wait
Low Quality + High Opportunity = value trap, avoid
Low Quality + Low Opportunity = strong avoid

═══════════════════════════════════════════════════════════════
COMPANY: {company} ({ticker})
Sector: {sector} | Industry: {industry}
Analysis date: {today}
═══════════════════════════════════════════════════════════════

PORTER'S FIVE FORCES (from 10-K):
Overall Moat Score: {moat_score}/5
{porter_details}
Moat Summary: {moat_summary}

FINANCIAL HISTORY ({years} years):
Revenue CAGR: {cagr}%
Year | Revenue($B) | Gross% | Op% | Net% | FCF% | ROIC% | D/E
{financial_table}

CURRENT VALUATION:
Price: ${price} | P/E: {pe}x | Fwd P/E: {fpe}x | EV/EBITDA: {evebitda}x
PEG: {peg}x | vs 52w High: {pct_high}% | Mkt Cap: ${mktcap}B
Dividend: {div_yield}% | Analyst Target: ${analyst_target} | Consensus: {recommendation} | Beta: {beta}

DIMENSION 1 — STRUCTURAL POSITIONING:
Evaluate megatrend exposure (AI, energy transition, healthcare innovation, digital infrastructure, demographics, deglobalization, resource scarcity, financial evolution). Is company PRIMARY (directly in value chain), SECONDARY (indirect), PERIPHERAL, or HEADWIND?
Evaluate necessity/demand resilience, moat trajectory, TAM evolution, technology disruption resilience.

DIMENSION 2 — COMPETITIVE MOAT:
Deep analysis of all 5 Porter forces with 10-K evidence AND forward-looking trend for each.

DIMENSION 3 — FINANCIAL QUALITY:
Gross margin trend (pricing power), ROIC vs 15%/25% thresholds, FCF vs net margin gap, debt trajectory, recession resilience.

DIMENSION 4 — VALUATION:
PEG analysis, EV/EBITDA vs sector norms, Reverse DCF (what growth rate does current market cap imply at 10% discount rate?), margin of safety calculation.

ARCHETYPE CLASSIFICATION:
MEGATREND MONOPOLIST: Quality>8.5 — primary megatrend + near-monopoly + strong financials
MEGATREND RIDER: Quality 7-8.5, Structural>7 — strong megatrend but competitive market
QUALITY COMPOUNDER: Quality 7-8.5, Moat>7, Structural 5-7 — excellent moat, stable growth
HIDDEN GEM: Quality 6.5-8, Opportunity>7 — strong quality but undervalued
CASH COW: Structural 3-5, Moat>6, Financial>7 — low growth, high quality, reliable
TURNAROUND CANDIDATE: Quality>6, Financial 3-5, Structural>6 — structurally sound, impaired financials
VALUE TRAP: Quality<5 — looks cheap but structurally impaired
COMMODITY CYCLICAL: Moat<4 — no durable advantage, cyclical earnings

Respond ONLY with valid JSON. No markdown. No preamble. No trailing commas. Double quotes only.

{{
  "ticker": "{ticker}",
  "company": "{company}",
  "analysis_date": "{today}",
  "sector": "{sector}",
  "industry": "{industry}",

  "scores": {{
    "structural_score": <1-10>,
    "moat_score": <1-10>,
    "financial_score": <1-10>,
    "valuation_score": <1-10>,
    "quality_score": <structural*0.4 + moat*0.35 + financial*0.25>,
    "opportunity_score": <valuation*0.6 + quality*0.4>,
    "combined_score": <quality*0.6 + opportunity*0.4>
  }},

  "archetype": "<MEGATREND MONOPOLIST / MEGATREND RIDER / QUALITY COMPOUNDER / HIDDEN GEM / CASH COW / TURNAROUND CANDIDATE / VALUE TRAP / COMMODITY CYCLICAL>",
  "archetype_reasoning": "<3-4 sentences explaining why>",

  "verdict": "<strong buy / buy / hold / avoid / strong avoid>",
  "verdict_split": {{
    "quality_verdict": "<exceptional / strong / average / weak / avoid>",
    "timing_verdict": "<great entry / good entry / fair entry / wait / expensive / very expensive>"
  }},
  "time_horizon": "<short-term (<1yr) / medium-term (1-3yr) / long-term (3yr+)>",
  "conviction_level": "<very high / high / medium / low>",

  "structural_analysis": {{
    "score": <1-10>,
    "megatrend_exposure_score": <1-10>,
    "megatrend_type": "<primary beneficiary / secondary beneficiary / peripheral / headwind>",
    "megatrends_exposed_to": ["<megatrend 1>", "<megatrend 2>"],
    "megatrend_analysis": "<5-6 sentences: which megatrends, how directly, value chain position, how position becomes more or less valuable as megatrend scales>",
    "necessity_score": <1-10>,
    "necessity_analysis": "<3-4 sentences: essential vs discretionary, recession behavior, demand elasticity>",
    "moat_trajectory_score": <1-10>,
    "moat_trajectory_analysis": "<5-6 sentences: barriers rising or falling, switching costs, compounding advantages or erosion>",
    "tam_evolution_score": <1-10>,
    "tam_evolution_analysis": "<3-4 sentences: TAM direction, pricing power, new adjacencies>",
    "technology_resilience_score": <1-10>,
    "technology_resilience_analysis": "<3-4 sentences: disruption risk, specific threats, R&D adequacy>",
    "structural_summary": "<6-7 sentences: will this company be stronger or weaker in 10 years? What is the single most important structural fact?>"
  }},

  "moat_analysis": {{
    "score": <1-10>,
    "rivalry": {{
      "score": <1-5>,
      "trend": "<strengthening / stable / weakening>",
      "analysis": "<4-5 sentences with 10-K evidence and forward view>",
      "key_competitors": ["<competitor 1>", "<competitor 2>"]
    }},
    "new_entrants": {{
      "score": <1-5>,
      "trend": "<strengthening / stable / weakening>",
      "analysis": "<4-5 sentences>",
      "biggest_threat": "<most credible entrant>"
    }},
    "substitutes": {{
      "score": <1-5>,
      "trend": "<strengthening / stable / weakening>",
      "analysis": "<4-5 sentences>",
      "key_substitute": "<most credible substitute>"
    }},
    "buyer_power": {{
      "score": <1-5>,
      "trend": "<strengthening / stable / weakening>",
      "analysis": "<4-5 sentences>"
    }},
    "supplier_power": {{
      "score": <1-5>,
      "trend": "<strengthening / stable / weakening>",
      "analysis": "<4-5 sentences>"
    }},
    "moat_confirmed_by_financials": <true or false>,
    "moat_durability": "<widening / stable / narrowing / at risk>",
    "overall_moat_verdict": "<4-5 sentences synthesizing all 5 forces and forward trajectory>"
  }},

  "financial_analysis": {{
    "score": <1-10>,
    "margin_trend": "<strongly improving / improving / stable / deteriorating / strongly deteriorating>",
    "roic_assessment": "<exceptional (>25%) / strong (15-25%) / adequate (10-15%) / weak (<10%)>",
    "earnings_quality": "<high / medium / low>",
    "balance_sheet_health": "<fortress / strong / adequate / stretched / concerning>",
    "recession_resilience": "<very high / high / medium / low / very low>",
    "deep_analysis": "<6-7 sentences with specific numbers>"
  }},

  "valuation_analysis": {{
    "score": <1-10>,
    "overall_assessment": "<very cheap / cheap / fair / expensive / very expensive>",
    "peg_signal": "<very cheap / cheap / fair / expensive / very expensive>",
    "ev_ebitda_signal": "<very cheap / cheap / fair / expensive / very expensive>",
    "implied_10yr_growth_rate": "<e.g. 12% per year>",
    "implied_growth_realistic": <true or false>,
    "implied_growth_assessment": "<specific reasoning>",
    "estimated_intrinsic_value_conservative": "<e.g. $180>",
    "estimated_intrinsic_value_optimistic": "<e.g. $240>",
    "current_vs_intrinsic": "<e.g. +35% premium or -15% discount>",
    "strong_buy_price": "<specific price>",
    "watchlist_price": "<price to start watching>",
    "valuation_deep_analysis": "<6-7 sentences: PEG, EV/EBITDA vs sector norms, reverse DCF, margin of safety>"
  }},

  "risk_matrix": {{
    "competitive_disruption": "<Low / Medium / High / Critical>",
    "competitive_disruption_explanation": "<3 sentences>",
    "regulatory": "<Low / Medium / High / Critical>",
    "regulatory_explanation": "<3 sentences>",
    "macro_sensitivity": "<Low / Medium / High / Critical>",
    "macro_explanation": "<3 sentences>",
    "balance_sheet": "<Low / Medium / High / Critical>",
    "balance_sheet_explanation": "<3 sentences>",
    "management": "<Low / Medium / High / Critical>",
    "management_explanation": "<3 sentences>",
    "geopolitical": "<Low / Medium / High / Critical>",
    "geopolitical_explanation": "<3 sentences>",
    "technology_obsolescence": "<Low / Medium / High / Critical>",
    "technology_explanation": "<3 sentences>",
    "esg": "<Low / Medium / High / Critical>",
    "esg_explanation": "<3 sentences>",
    "overall_risk_level": "<Low / Medium / High / Critical>",
    "top_3_risks": ["<risk 1: specific scenario>", "<risk 2>", "<risk 3>"]
  }},

  "sector_analysis": {{
    "sector_outlook_5_10yr": "<strong growth / moderate growth / stable / declining>",
    "company_competitive_position": "<dominant leader / strong #2 / mid-tier / weak>",
    "structural_tailwinds": ["<tailwind with magnitude>", "<tailwind 2>", "<tailwind 3>"],
    "structural_headwinds": ["<headwind with magnitude>", "<headwind 2>", "<headwind 3>"],
    "megatrend_impact": "<5-6 sentences>",
    "recession_history": "<3-4 sentences on 2008 and 2020 performance>",
    "disruption_threats": "<4-5 sentences>",
    "better_sector_alternatives": ["<ticker: specific reason>"]
  }},

  "investment_verdict": {{
    "key_thesis": "<6-7 sentences, direct, specific numbers, reference quality vs opportunity score>",
    "upside_catalysts": ["<specific quantifiable catalyst with timeline>", "<catalyst 2>", "<catalyst 3>"],
    "downside_risks": ["<specific quantifiable risk with trigger>", "<risk 2>", "<risk 3>"],
    "strong_buy_at": "<specific price>",
    "watchlist_at": "<price to start watching>",
    "exit_trigger": "<specific event or price that changes thesis>",
    "position_sizing_note": "<core position (5-10%) / moderate (2-5%) / small (1-2%) / avoid>"
  }},

  "comparable_companies": ["<ticker: why comparable>", "<ticker>"],
  "data_completeness": "<High / Medium / Low>",
  "data_source_notes": "<caveats about data quality>"
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
        rationale = f.get("rationale", "")[:150]
        lines.append(f"  {label}: {score}/5 — {rationale}")
    risks = porter.get("key_risks", [])
    if risks:
        lines.append(f"\nKey risks from 10-K: {' | '.join(risks[:3])}")
    return "\n".join(lines)

def build_financial_table(history: list) -> str:
    lines = []
    for h in history:
        lines.append(
            f"{h['year']} | ${h['revenue_B']}B | "
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
                "max_tokens": 8000,
                "temperature": 0.1,
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  LLM error: {e}")
        return None
def parse_json(raw: str) -> dict | None:
    raw = re.sub(r'```[a-z]*\s*', '', raw).strip()
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

    porter_path = f"{DATA_OUTPUT}/{ticker}_porter.json"
    fin_path    = f"{DATA_OUTPUT}/{ticker}_financials.json"

    if not os.path.exists(porter_path):
        print(f"{ticker}: Porter analysis missing")
        return None
    if not os.path.exists(fin_path):
        print(f"{ticker}: financials missing")
        return None

    with open(porter_path) as f:
        porter = json.load(f)
    with open(fin_path) as f:
        fin = json.load(f)

    c       = fin.get("current", {})
    history = fin.get("history", [])
    cagr    = fin.get("revenue_cagr")

    prompt = ANALYSIS_PROMPT.format(
        ticker=ticker,
        company=porter.get("company", ticker),
        sector=c.get("sector", "Unknown"),
        industry=c.get("industry", "Unknown"),
        moat_score=porter.get("moat_score", "?"),
        moat_summary=porter.get("moat_summary", ""),
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
        analyst_target=c.get("analyst_target", "n/a"),
        recommendation=c.get("recommendation", "n/a"),
        beta=c.get("beta", "n/a"),
        today=str(date.today()),
    )

    print(f"{ticker}: calling LLM for integrated analysis...")
    raw = call_llm(prompt)
    if not raw:
        print(f"{ticker}: LLM did not respond")
        return None

    result = parse_json(raw)
    if not result:
        print(f"{ticker}: JSON parsing failed")
        result = {"ticker": ticker, "error": "parse_failed", "raw": raw}

    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"{ticker}: saved — score: {result.get('scores', {}).get('combined_score')}/10 | {result.get('verdict')}")
    return result

def print_analysis(ticker: str):
    path = f"{DATA_OUTPUT}/{ticker}_investment.json"
    if not os.path.exists(path):
        print(f"{ticker}: no analysis found")
        return
    with open(path) as f:
        d = json.load(f)
    if "error" in d:
        print(f"{ticker}: error — {d['error']}")
        return

    s = d.get("scores", {})
    print(f"\n{'='*65}")
    print(f"{d['ticker']} — {d['company']}")
    print(f"{'='*65}")
    print(f"  Archetype:         {d.get('archetype')}")
    print(f"  Quality Score:     {s.get('quality_score')}/10")
    print(f"  Opportunity Score: {s.get('opportunity_score')}/10")
    print(f"  Combined Score:    {s.get('combined_score')}/10")
    print(f"  Verdict:           {d.get('verdict', '').upper()}")
    vs = d.get("verdict_split", {})
    print(f"  Quality:           {vs.get('quality_verdict')}")
    print(f"  Timing:            {vs.get('timing_verdict')}")
    va = d.get("valuation_analysis", {})
    print(f"  Strong buy at:     {va.get('strong_buy_price')}")
    print(f"  Watchlist at:      {va.get('watchlist_price')}")
    iv = d.get("investment_verdict", {})
    print(f"\n  Thesis: {iv.get('key_thesis', '')[:300]}")

if __name__ == "__main__":
    for ticker in ["MSFT", "GOOGL", "AAPL"]:
        rm_path = f"data/output/{ticker}_investment.json"
        if os.path.exists(rm_path):
            os.remove(rm_path)
        result = analyze(ticker)
        if result:
            print_analysis(ticker)
