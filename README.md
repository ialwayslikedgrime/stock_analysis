
# Porter Moat Analyzer — Architecture & Economic Rationale

## Project Philosophy

This project is grounded in a core microeconomic principle: the sustainable
profitability of a company depends on its distance from perfect competition.
The closer a company is to a monopoly (entry barriers, pricing power, absence
of substitutes), the higher its long-term fair value.

The goal is to automate the identification of such companies within the S&P 500,
combining qualitative analysis (Porter's Five Forces) with quantitative analysis
(historical financial data).

---

## File Structure & Rationale

### `src/universe.py`
**What it does:** Downloads the list of S&P 500 companies from Wikipedia.

**Why the S&P 500:**
These are the most liquid and best-documented public companies in the world.
Liquidity matters for retail investors — a company with an excellent moat but
thin trading volume is hard to enter or exit without moving the price.
Wikipedia keeps the list updated in real time as index changes occur.

---

### `src/edgar.py`
**What it does:** Downloads the annual 10-K filing for each company from the
SEC EDGAR archive.

**Why the 10-K:**
It is the most complete and legally reliable document that exists for a US-listed
company. It is signed by the CEO and CFO under oath (Sarbanes-Oxley Act, 2002) —
misrepresentation carries criminal penalties. It contains the business description,
competitive risks, and financial statements certified by external auditors.

**Why EDGAR and not other sources:**
EDGAR is the primary, free, official source. Everything else (Bloomberg, FMP,
Yahoo Finance) ultimately derives from it.

**Known limitation:**
10-Ks are backward-looking. They may not capture disruptions currently underway.
This is why we supplement them with recent market data.

---

### `src/extractor.py`
**What it does:** Extracts the relevant sections from the raw 10-K (HTML/iXBRL)
to avoid sending the entire document (1–8 million characters) to the LLM.

**Sections extracted and why:**

- **Item 1 (Business):** Describes the business model, products, and target markets.
  This is the foundation for evaluating market power and entry barriers.

- **Item 1A (Risk Factors):** The company itself describes competitive threats.
  Written by lawyers for liability protection, so it tends toward excess — but
  the risks mentioned are real and legally acknowledged.

- **Item 3 (Legal Proceedings):** Antitrust lawsuits signal that someone considers
  the company a monopoly — exactly what we are looking for.

- **Item 7 (MD&A):** Management discusses results in their own words. Reveals
  margin pressure, competitive shifts, and strategic investments.

- **Item 8 (Financial Statements):** The audited numbers. The basis for computing
  ROIC, margins, and free cash flow.

**Why not send everything to Claude:**
Claude Sonnet's context window is ~200k tokens (~150k characters). Microsoft's
10-K is 8 million characters. Even ignoring the limit, sending everything would
cost ~$24 per company vs ~$0.03 with the extract. Across 500 companies, that
is $12,000 vs $15.

---

### `src/analyzer.py`
**What it does:** Sends the extracted text to the LLM (Claude via OpenRouter)
and receives a Porter's Five Forces analysis in structured JSON format.

**Why Porter's Five Forces:**
Michael Porter (Harvard, 1979) demonstrated that the structural profitability
of an industry depends on five competitive forces. Each force reduces the
company's pricing power:

1. **Rivalry** — direct competitors compressing margins
2. **New entrants** — who could enter and erode market share
3. **Substitutes** — alternative products that cap pricing
4. **Buyer power** — customers negotiating lower prices
5. **Supplier power** — suppliers raising input costs

A company with all five forces in its favor is, in practice, a monopoly.
These are the businesses Warren Buffett calls "moats" — competitive advantages
that are structurally difficult to attack.

**Why use an LLM for this analysis:**
Porter's Five Forces require qualitative judgment that cannot be extracted
directly from numbers. An LLM trained on billions of documents can read a 10-K
and identify entry barriers, switching costs, and network effects — analysis
that would otherwise require a senior human analyst.

**Fallback system:**
If text extraction fails (non-standard format), the system uses the LLM's
prior knowledge of the company, clearly flagging what comes from the document
versus what is inferred.

---

### `src/financials.py`
**What it does:** Downloads historical financial data (income statements, balance
sheets, cash flows, prices) and computes key indicators.

**Why financial data after Porter:**
Porter's Five Forces identify the theoretical moat. Financial data verifies
whether the moat actually exists in the numbers. A real moat manifests as:

- **Stable or growing gross margins** — the company does not need to cut prices
  to compete
- **Persistent ROIC > WACC** — invested capital generates returns above its cost,
  proving that entry barriers are working
- **High FCF margin** — earnings convert to real cash, not just accounting profit
- **Margins that hold during recessions** — the ultimate stress test of a moat

**Why 10–15 years of history:**
Economic theory on margin mean reversion (Fama-French, McKinsey Global Institute)
shows that margins tend to converge toward the industry average within 7–10 years.
If margins remain exceptional after 10 years, the moat is structural. Including
at least one recession (2020, 2022) is essential to test resilience.

**Indicators computed:**

| Indicator | Formula | What it measures |
|---|---|---|
| Gross Margin % | gross profit / revenue | Pricing power |
| Operating Margin % | operating income / revenue | Operational efficiency |
| Net Margin % | net income / revenue | Net profitability |
| FCF Margin % | free cash flow / revenue | Earnings quality |
| ROIC % | net income / (debt + equity) | Return on invested capital |
| D/E | total debt / equity | Financial solidity |
| Revenue CAGR | compound annual growth rate | Moat expansion |

---

### `src/reporter.py`
**What it does:** Aggregates all results into a final ranking and generates
readable reports (CSV + narrative text).

**Ranking logic:**
The moat_score (weighted average of the Five Forces, 1–5) is the primary
sorting criterion. Valuation is intentionally kept separate — a company with
a perfect moat but a P/E of 100x may still be a poor investment at current
prices. Valuation is a second-pass filter, not part of the moat score.

---

## Full Data Flow

## Full Data Flow
S&P 500 list (Wikipedia)
↓
10-K download (EDGAR)
↓
Text extraction (Items 1, 1A, 3, 7, 8)
↓
Porter Analysis (Claude via OpenRouter)  →  Structured JSON
↓
Financial Data (yfinance)
↓
Financial Analysis (Claude)             →  Integrated synthesis
↓
Reporter → CSV + Narrative Report

---

## Known Limitations

**1. Backward-looking data**
10-Ks describe the past. An ongoing disruption (e.g. AI eroding Google Search's
moat) may not yet be visible in the filing.

**2. Narrative bias**
Item 1 is written by the company with positive framing. Item 1A tends toward
legal boilerplate excess. The LLM must distinguish genuine risk from standard
legal language.

**3. LLM hallucination risk**
For less-covered companies or complex sectors, the LLM may overestimate the moat
based on prior knowledge rather than the document text. This is why we flag the
`data_source` field in every output.

**4. No valuation layer (yet)**
The system identifies companies with strong moats but does not assess whether
the current price is reasonable. An excellent company bought at P/E 80x can
underperform for years.

**5. US-only universe**
EDGAR covers only US-listed companies. European or Asian companies with
exceptional moats (LVMH, ASML, Toyota) are not included in this version.

---

## Technical Decisions

| Decision | Rationale |
|---|---|
| Python | Richest ecosystem for data science and financial APIs |
| Claude via OpenRouter | Model flexibility without code changes; best-in-class for long document analysis and structured JSON output |
| Disk cache | API calls cost money and time. Caching prevents re-analyzing what is already done and allows resuming interrupted runs |
| Structured JSON output | Enables automated comparison across 500 companies. Free-form text cannot be aggregated or ranked |
| EDGAR over FMP/Bloomberg | Primary source, free, no rate limits on document downloads |
| yfinance for market data | Free, reliable, 15+ years of history, no registration required |

