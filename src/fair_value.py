def get_opportunity_score(ticker: str) -> dict:
    # Legge fair value dal JSON (calcolato dal LLM mesi fa)
    inv = load_investment(ticker)
    fair_value_low = inv["valuation_analysis"]["estimated_intrinsic_value_conservative"]
    fair_value_high = inv["valuation_analysis"]["estimated_intrinsic_value_optimistic"]
    
    # Prende prezzo corrente da yfinance (gratis, real-time)
    current_price = yf.Ticker(ticker).info["currentPrice"]
    
    # Calcola discount/premium
    fair_value_mid = (fair_value_low + fair_value_high) / 2
    premium = (current_price / fair_value_mid - 1) * 100
    
    # Opportunity score dinamico
    if premium < -25: return {"score": 10, "signal": "strong buy"}
    if premium < -15: return {"score": 8, "signal": "buy"}
    if premium < -5:  return {"score": 6, "signal": "accumulate"}
    if premium < +10: return {"score": 5, "signal": "hold"}
    if premium < +25: return {"score": 3, "signal": "expensive"}
    return {"score": 1, "signal": "very expensive"}