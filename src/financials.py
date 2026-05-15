import requests
import json
import os
import time
import yfinance as yf
from dotenv import load_dotenv
from config.settings import DATA_OUTPUT

load_dotenv()
FMP_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/stable"

def fmp_get(endpoint: str, params: dict = {}) -> list | dict | None:
    params["apikey"] = FMP_KEY
    time.sleep(0.3)
    r = requests.get(f"{FMP_BASE}/{endpoint}", params=params)
    if r.status_code == 200:
        return r.json()
    print(f"  FMP error {r.status_code}: {r.text[:150]}")
    return None

def get_financials(ticker: str, years: int = 5) -> dict | None:
    cache_path = f"{DATA_OUTPUT}/{ticker}_financials.json"
    if os.path.exists(cache_path):
        print(f"{ticker}: caricato da cache")
        with open(cache_path) as f:
            return json.load(f)

    print(f"{ticker}: scarico dati FMP...")
    income   = fmp_get("income-statement",       {"symbol": ticker, "limit": years})
    balance  = fmp_get("balance-sheet-statement", {"symbol": ticker, "limit": years})
    cashflow = fmp_get("cash-flow-statement",     {"symbol": ticker, "limit": years})

    if not income or not balance or not cashflow:
        print(f"{ticker}: dati FMP incompleti")
        return None

    history = []
    for i, inc in enumerate(income):
        bal = balance[i] if i < len(balance) else {}
        cf  = cashflow[i] if i < len(cashflow) else {}

        rev = inc.get("revenue", 0)
        gp  = inc.get("grossProfit", 0)
        oi  = inc.get("operatingIncome", 0)
        ni  = inc.get("netIncome", 0)
        ocf = cf.get("operatingCashFlow", 0)
        cpx = cf.get("capitalExpenditure", 0)  # negativo in FMP
        fcf = ocf + cpx
        eq  = bal.get("totalStockholdersEquity", 1)
        ltd = bal.get("totalDebt", 0)

        history.append({
            "year":             inc.get("fiscalYear"),
            "date":             inc.get("date"),
            "revenue_B":        round(rev / 1e9, 1),
            "gross_margin":     round(gp / rev * 100, 1) if rev and gp else None,
            "operating_margin": round(oi / rev * 100, 1) if rev and oi else None,
            "net_margin":       round(ni / rev * 100, 1) if rev and ni else None,
            "fcf_margin":       round(fcf / rev * 100, 1) if rev and fcf else None,
            "roic":             round(ni / (ltd + eq) * 100, 1) if (ltd + eq) and ni else None,
            "debt_equity":      round(ltd / eq, 2) if eq else 0.0,
        })

    # Revenue CAGR
    cagr = None
    if len(history) >= 2:
        rev_old = history[-1]["revenue_B"]
        rev_new = history[0]["revenue_B"]
        n = len(history) - 1
        cagr = round(((rev_new / rev_old) ** (1/n) - 1) * 100, 1) if rev_old else None

    # Dati mercato da yfinance
    print(f"{ticker}: scarico dati mercato...")
    current = {}
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        high  = info.get("fiftyTwoWeekHigh")
        current = {
            "price":             price,
            "pe_ratio":          info.get("trailingPE"),
            "forward_pe":        info.get("forwardPE"),
            "market_cap_B":      round(info.get("marketCap", 0) / 1e9, 1),
            "ev_ebitda":         info.get("enterpriseToEbitda"),
            "price_to_fcf":      info.get("priceToFreeCashflows"),
            "52w_high":          high,
            "52w_low":           info.get("fiftyTwoWeekLow"),
            "dividend_yield":    info.get("dividendYield"),
            "sector":            info.get("sector"),
            "industry":          info.get("industry"),
            "pct_from_52w_high": round((price / high - 1) * 100, 1) if price and high else None,
        }
    except Exception as e:
        print(f"{ticker}: yfinance error: {e}")

    result = {
        "ticker":         ticker,
        "revenue_cagr":   cagr,
        "years_analyzed": len(history),
        "current":        current,
        "history":        history,
    }

    os.makedirs(DATA_OUTPUT, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"{ticker}: salvati {len(history)} anni")
    return result

def print_financials(ticker: str):
    path = f"{DATA_OUTPUT}/{ticker}_financials.json"
    if not os.path.exists(path):
        print(f"{ticker}: nessun dato trovato")
        return
    with open(path) as f:
        data = json.load(f)
    c = data.get("current", {})
    print(f"\n{'='*70}")
    print(f"{ticker} | {c.get('sector')} — {c.get('industry')}")
    print(f"{'='*70}")
    print(f"  Price: ${c.get('price')}  |  P/E: {round(c.get('pe_ratio'),1) if c.get('pe_ratio') else '-'}  |  Fwd P/E: {round(c.get('forward_pe'),1) if c.get('forward_pe') else '-'}")
    print(f"  EV/EBITDA: {c.get('ev_ebitda')}  |  Mkt Cap: ${c.get('market_cap_B')}B")
    print(f"  52w High: ${c.get('52w_high')}  |  vs High: {c.get('pct_from_52w_high')}%")
    print(f"  Revenue CAGR ({data.get('years_analyzed')}yr): {data.get('revenue_cagr')}%")
    print(f"\n  {'Year':<6} {'Rev($B)':>8} {'Gross%':>7} {'Op%':>6} {'Net%':>6} {'FCF%':>6} {'ROIC%':>7} {'D/E':>6}")
    print(f"  {'-'*62}")
    for h in data["history"]:
        print(f"  {h['year']:<6} {h['revenue_B']:>7.1f}  "
              f"{str(h['gross_margin'] or '-'):>6}% "
              f"{str(h['operating_margin'] or '-'):>5}% "
              f"{str(h['net_margin'] or '-'):>5}% "
              f"{str(h['fcf_margin'] or '-'):>5}% "
              f"{str(h['roic'] or '-'):>6}% "
              f"{str(h['debt_equity']):>6}")

if __name__ == "__main__":
    for ticker in ["AAPL", "MSFT", "GOOGL"]:
        get_financials(ticker, years=5)
        print_financials(ticker)
