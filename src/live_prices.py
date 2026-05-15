import yfinance as yf
import json
import os
import glob
from datetime import datetime
from config.settings import DATA_OUTPUT

def update_prices():
    """
    Aggiorna prezzi e ratios di mercato per tutte le aziende analizzate.
    Non chiama il LLM — usa solo yfinance.
    Ricalcola l'opportunity score dinamicamente.
    """
    updated = 0
    failed = []

    inv_files = glob.glob(f"{DATA_OUTPUT}/*_investment.json")
    print(f"Aggiornamento prezzi per {len(inv_files)} aziende...")

    for inv_path in inv_files:
        ticker = os.path.basename(inv_path).replace("_investment.json", "")
        fin_path = f"{DATA_OUTPUT}/{ticker}_financials.json"

        if not os.path.exists(fin_path):
            continue

        try:
            with open(fin_path) as f:
                fin = json.load(f)
            with open(inv_path) as f:
                inv = json.load(f)

            # Aggiorna solo i dati di mercato
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            high  = info.get("fiftyTwoWeekHigh")

            if not price:
                failed.append(ticker)
                continue

            # Aggiorna current nel file financials
            fin["current"].update({
                "price":                price,
                "pe_ratio":             info.get("trailingPE"),
                "forward_pe":           info.get("forwardPE"),
                "ev_ebitda":            info.get("enterpriseToEbitda"),
                "market_cap_B":         round(info.get("marketCap",0)/1e9,1),
                "52w_high":             high,
                "52w_low":              info.get("fiftyTwoWeekLow"),
                "pct_from_52w_high":    round((price/high-1)*100,1) if high else None,
                "52w_change":           round(info.get("52WeekChange",0)*100,1),
                "gross_margin_ttm":     round(info.get("grossMargins",0)*100,1),
                "operating_margin_ttm": round(info.get("operatingMargins",0)*100,1),
                "net_margin_ttm":       round(info.get("profitMargins",0)*100,1),
                "return_on_equity":     round(info.get("returnOnEquity",0)*100,1),
                "return_on_assets":     round(info.get("returnOnAssets",0)*100,1),
                "revenue_growth_yoy":   round(info.get("revenueGrowth",0)*100,1),
                "analyst_target":       info.get("targetMeanPrice"),
                "recommendation":       info.get("recommendationKey"),
            })
            fin["last_price_update"] = datetime.now().isoformat()

            # Ricalcola opportunity score dinamicamente
            # basato su prezzo corrente vs fair value stimato dal LLM
            va = inv.get("valuation_analysis", {})
            try:
                fv_low  = float(va.get("estimated_intrinsic_value_conservative","0").replace("$","").replace(",",""))
                fv_high = float(va.get("estimated_intrinsic_value_optimistic","0").replace("$","").replace(",",""))
                fv_mid  = (fv_low + fv_high) / 2 if fv_low and fv_high else 0

                if fv_mid > 0:
                    premium = (price / fv_mid - 1) * 100
                    # Opportunity score dinamico
                    if premium < -30:   opp_score = 10.0
                    elif premium < -20: opp_score = 9.0
                    elif premium < -10: opp_score = 7.5
                    elif premium < -5:  opp_score = 6.5
                    elif premium < 5:   opp_score = 5.5
                    elif premium < 15:  opp_score = 4.5
                    elif premium < 30:  opp_score = 3.5
                    elif premium < 50:  opp_score = 2.5
                    else:               opp_score = 1.5

                    # Aggiorna scores nel file investment
                    s = inv.get("scores", {})
                    quality = s.get("quality_score", 0)
                    s["opportunity_score"]    = opp_score
                    s["combined_score"]       = round(quality*0.6 + opp_score*0.4, 1)
                    s["price_vs_fair_value"]  = round(premium, 1)
                    inv["scores"] = s
                    inv["last_price_update"]  = datetime.now().isoformat()

                    # Aggiorna verdict in base ai nuovi score
                    if quality >= 7 and opp_score >= 8:
                        inv["verdict"] = "strong buy"
                    elif quality >= 6.5 and opp_score >= 6.5:
                        inv["verdict"] = "buy"
                    elif opp_score < 3:
                        inv["verdict"] = "avoid" if quality < 6 else "hold"
                    elif opp_score < 4.5:
                        inv["verdict"] = "hold"

            except (ValueError, TypeError):
                pass

            with open(fin_path, "w") as f:
                json.dump(fin, f, indent=2)
            with open(inv_path, "w") as f:
                json.dump(inv, f, indent=2)

            updated += 1

        except Exception as e:
            failed.append(ticker)
            print(f"  {ticker}: error — {e}")

    print(f"\n✓ Updated: {updated} | Failed: {len(failed)}")
    if failed:
        print(f"  Failed: {failed}")

    # Rigenera dashboard automaticamente
    try:
        import generate_dashboard
        generate_dashboard.generate()
    except Exception as e:
        print(f"  Dashboard error: {e}")

if __name__ == "__main__":
    update_prices()
