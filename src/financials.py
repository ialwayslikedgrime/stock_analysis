import requests
import json
import os
import time
import yfinance as yf
from dotenv import load_dotenv
from config.settings import DATA_OUTPUT, EDGAR_HEADERS

load_dotenv()
FMP_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/stable"

def fmp_get(endpoint: str, params: dict = {}) -> list | dict | None:
    params["apikey"] = FMP_KEY
    time.sleep(0.3)
    r = requests.get(f"{FMP_BASE}/{endpoint}", params=params)
    if r.status_code == 200:
        return r.json()
    return None

def get_yfinance_history(ticker: str) -> list:
    """Bilanci storici da yfinance."""
    history = []
    try:
        yf_ticker = yf.Ticker(ticker)
        inc = yf_ticker.financials
        bal = yf_ticker.balance_sheet
        cf  = yf_ticker.cashflow

        for col in inc.columns:
            year = str(col.year)
            try:
                rev = float(inc.loc["Total Revenue", col]) if "Total Revenue" in inc.index else 0
                gp  = float(inc.loc["Gross Profit", col]) if "Gross Profit" in inc.index else 0
                oi  = float(inc.loc["Operating Income", col]) if "Operating Income" in inc.index else 0
                ni  = float(inc.loc["Net Income", col]) if "Net Income" in inc.index else 0
                ocf = float(cf.loc["Operating Cash Flow", col]) if "Operating Cash Flow" in cf.index and col in cf.columns else 0
                cpx = float(cf.loc["Capital Expenditure", col]) if "Capital Expenditure" in cf.index and col in cf.columns else 0
                eq  = float(bal.loc["Stockholders Equity", col]) if "Stockholders Equity" in bal.index and col in bal.columns else 1
                ltd = float(bal.loc["Long Term Debt", col]) if "Long Term Debt" in bal.index and col in bal.columns else 0
                fcf = ocf + cpx

                if rev > 0:
                    history.append({
                        "year":             year,
                        "revenue_B":        round(rev / 1e9, 1),
                        "gross_margin":     round(gp / rev * 100, 1) if gp else None,
                        "operating_margin": round(oi / rev * 100, 1) if oi else None,
                        "net_margin":       round(ni / rev * 100, 1) if ni else None,
                        "fcf_margin":       round(fcf / rev * 100, 1) if fcf else None,
                        "roic":             round(ni / (ltd + eq) * 100, 1) if (ltd + eq) and ni else None,
                        "debt_equity":      round(ltd / eq, 2) if eq and ltd else 0.0,
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"  yfinance bilanci error: {e}")

    return sorted(history, key=lambda x: x["year"], reverse=True)

def get_market_data(ticker: str) -> dict:
    """Dati di mercato da yfinance."""
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        high  = info.get("fiftyTwoWeekHigh")
        return {
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
            "beta":              info.get("beta"),
            "analyst_target":    info.get("targetMeanPrice"),
            "recommendation":    info.get("recommendationKey"),
            "pct_from_52w_high": round((price / high - 1) * 100, 1) if price and high else None,
        }
    except Exception as e:
        print(f"  yfinance market error: {e}")
        return {}

def get_financials(ticker: str, years: int = 5) -> dict | None:
    cache_path = f"{DATA_OUTPUT}/{ticker}_financials.json"
    if os.path.exists(cache_path):
        print(f"{ticker}: caricato da cache")
        with open(cache_path) as f:
            return json.load(f)

    print(f"{ticker}: scarico dati finanziari...")
    source = "yfinance"
    history = []

    # Prova FMP prima
    fmp_income   = fmp_get("income-statement",        {"symbol": ticker, "limit": years})
    fmp_balance  = fmp_get("balance-sheet-statement", {"symbol": ticker, "limit": years})
    fmp_cashflow = fmp_get("cash-flow-statement",     {"symbol": ticker, "limit": years})

    if fmp_income and fmp_balance and fmp_cashflow:
        source = "fmp"
        print(f"{ticker}: usando FMP")
        for i, inc in enumerate(fmp_income):
            bal = fmp_balance[i] if i < len(fmp_balance) else {}
            cf  = fmp_cashflow[i] if i < len(fmp_cashflow) else {}
            rev = inc.get("revenue", 0)
            gp  = inc.get("grossProfit", 0)
            oi  = inc.get("operatingIncome", 0)
            ni  = inc.get("netIncome", 0)
            ocf = cf.get("operatingCashFlow", 0)
            cpx = cf.get("capitalExpenditure", 0)
            fcf = ocf + cpx
            eq  = bal.get("totalStockholdersEquity", 1)
            ltd = bal.get("totalDebt", 0)
            if rev > 0:
                history.append({
                    "year":             inc.get("fiscalYear"),
                    "revenue_B":        round(rev / 1e9, 1),
                    "gross_margin":     round(gp / rev * 100, 1) if gp else None,
                    "operating_margin": round(oi / rev * 100, 1) if oi else None,
                    "net_margin":       round(ni / rev * 100, 1) if ni else None,
                    "fcf_margin":       round(fcf / rev * 100, 1) if rev and fcf else None,
                    "roic":             round(ni / (ltd + eq) * 100, 1) if (ltd + eq) and ni else None,
                    "debt_equity":      round(ltd / eq, 2) if eq else 0.0,
                })
    else:
        print(f"{ticker}: FMP non disponibile, uso yfinance")
        history = get_yfinance_history(ticker)

    # Dati mercato sempre da yfinance
    current = get_market_data(ticker)

    # CAGR
    cagr = None
    valid = [h for h in history if h.get("revenue_B")]
    if len(valid) >= 2:
        rev_old = valid[-1]["revenue_B"]
        rev_new = valid[0]["revenue_B"]
        n = len(valid) - 1
        cagr = round(((rev_new / rev_old) ** (1/n) - 1) * 100, 1) if rev_old else None

    result = {
        "ticker":         ticker,
        "data_source":    source,
        "revenue_cagr":   cagr,
        "years_analyzed": len(history),
        "current":        current,
        "history":        history,
    }

    os.makedirs(DATA_OUTPUT, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"{ticker}: salvati {len(history)} anni (fonte: {source})")
    return result

if __name__ == "__main__":
    for ticker in ["ABNB", "MO", "APA", "AFL", "ABT"]:
        result = get_financials(ticker)
        if result:
            c = result.get("current", {})
            print(f"\n{ticker}: P/E {c.get('pe_ratio')} | {len(result['history'])} anni dati")
