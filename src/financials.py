import requests
import json
import os
import time
from dotenv import load_dotenv
from config.settings import DATA_OUTPUT

load_dotenv()
FMP_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/stable"

def fmp_get(endpoint: str, params: dict = {}) -> list | dict | None:
    """Chiamata generica a FMP con rate limiting."""
    params["apikey"] = FMP_KEY
    url = f"{FMP_BASE}/{endpoint}"
    time.sleep(0.3)  # rispetta rate limit
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    print(f"  FMP error {r.status_code}: {r.text[:100]}")
    return None

def get_financials(ticker: str, years: int = 5) -> dict | None:
    """Scarica e calcola tutti gli indici finanziari per un ticker."""
    print(f"{ticker}: scarico dati finanziari...")

    income = fmp_get("income-statement", {"symbol": ticker, "limit": years})
    balance = fmp_get("balance-sheet-statement", {"symbol": ticker, "limit": years})
    cashflow = fmp_get("cash-flow-statement", {"symbol": ticker, "limit": years})
    quote = fmp_get("quote", {"symbol": ticker})

    if not income or not balance or not cashflow:
        print(f"{ticker}: dati incompleti")
        return None

    years_data = []
    for i, inc in enumerate(income):
        bal = balance[i] if i < len(balance) else {}
        cf = cashflow[i] if i < len(cashflow) else {}

        revenue = inc.get("revenue", 0)
        gross_profit = inc.get("grossProfit", 0)
        operating_income = inc.get("operatingIncome", 0)
        net_income = inc.get("netIncome", 0)
        op_cashflow = cf.get("operatingCashFlow", 0)
        capex = cf.get("capitalExpenditure", 0)
        total_debt = bal.get("totalDebt", 0)
        equity = bal.get("totalStockholdersEquity", 1)
        total_assets = bal.get("totalAssets", 1)
        cash = bal.get("cashAndCashEquivalents", 0)

        fcf = op_cashflow + capex  # capex è negativo in FMP

        years_data.append({
            "year": inc.get("fiscalYear"),
            "date": inc.get("date"),
            "revenue": revenue,
            "gross_margin": round(gross_profit / revenue * 100, 1) if revenue else None,
            "operating_margin": round(operating_income / revenue * 100, 1) if revenue else None,
            "net_margin": round(net_income / revenue * 100, 1) if revenue else None,
            "fcf": fcf,
            "fcf_margin": round(fcf / revenue * 100, 1) if revenue else None,
            "debt_equity": round(total_debt / equity, 2) if equity else None,
            "roic": round(net_income / (total_debt + equity) * 100, 1) if (total_debt + equity) else None,
        })

    # Calcola CAGR revenue
    if len(years_data) >= 2:
        rev_first = years_data[-1]["revenue"]
        rev_last = years_data[0]["revenue"]
        n = len(years_data) - 1
        cagr = round(((rev_last / rev_first) ** (1/n) - 1) * 100, 1) if rev_first else None
    else:
        cagr = None

    # Valutazione attuale dal quote
    current = {}
    if quote and isinstance(quote, list) and quote:
        q = quote[0]
        current = {
            "price": q.get("price"),
            "pe_ratio": q.get("pe"),
            "market_cap": q.get("marketCap"),
            "52w_high": q.get("yearHigh"),
            "52w_low": q.get("yearLow"),
            "price_vs_52w_high": round((q.get("price", 0) / q.get("yearHigh", 1) - 1) * 100, 1) if q.get("yearHigh") else None,
        }

    result = {
        "ticker": ticker,
        "revenue_cagr": cagr,
        "current": current,
        "history": years_data,
    }

    # Salva cache
    os.makedirs(DATA_OUTPUT, exist_ok=True)
    out_path = f"{DATA_OUTPUT}/{ticker}_financials.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"{ticker}: dati finanziari salvati")
    return result

def print_financials(ticker: str):
    """Stampa un summary leggibile."""
    path = f"{DATA_OUTPUT}/{ticker}_financials.json"
    if not os.path.exists(path):
        print(f"{ticker}: nessun dato finanziario trovato")
        return
    with open(path) as f:
        data = json.load(f)

    print(f"\n{'='*60}")
    print(f"{ticker} — Financial Summary")
    print(f"{'='*60}")
    c = data.get("current", {})
    print(f"  Price: ${c.get('price')}  |  P/E: {c.get('pe_ratio')}  |  Mkt Cap: ${c.get('market_cap', 0)/1e9:.0f}B")
    print(f"  52w High: ${c.get('52w_high')}  |  vs High: {c.get('price_vs_52w_high')}%")
    print(f"  Revenue CAGR ({len(data['history'])}yr): {data.get('revenue_cagr')}%")
    print(f"\n  {'Year':<8} {'Revenue':>10} {'GrossM%':>8} {'OpM%':>7} {'NetM%':>7} {'FCF_M%':>8} {'ROIC%':>7} {'D/E':>6}")
    print(f"  {'-'*65}")
    for y in data["history"]:
        print(f"  {y['year']:<8} ${y['revenue']/1e9:>8.1f}B {y['gross_margin']:>7}% {y['operating_margin']:>6}% {y['net_margin']:>6}% {y['fcf_margin']:>7}% {y['roic']:>6}% {y['debt_equity']:>6}")

if __name__ == "__main__":
    for ticker in ["AAPL", "MSFT", "GOOGL"]:
        get_financials(ticker)
        print_financials(ticker)
