import pandas as pd
import json
import os
from config.settings import DATA_OUTPUT

SCORE_LEGEND = """
SCORE LEGEND (1-5, higher = more favorable for the company):
  rivalry:       5 = near-monopoly, 1 = fierce competition
  new_entrants:  5 = very high barriers, 1 = easy to enter
  substitutes:   5 = no alternatives, 1 = many substitutes
  buyer_power:   5 = buyers have no leverage, 1 = buyers dictate price
  supplier_power:5 = suppliers have no leverage, 1 = suppliers dictate price
  moat_score:    weighted average of the above
"""

def load_all_results() -> list[dict]:
    results = []
    for fname in os.listdir(DATA_OUTPUT):
        if fname.endswith("_porter.json"):
            with open(f"{DATA_OUTPUT}/{fname}") as f:
                try:
                    results.append(json.load(f))
                except json.JSONDecodeError:
                    print(f"Errore parsing {fname}")
    return results

def build_summary_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        if "error" in r or "forces" not in r:
            continue
        forces = r["forces"]
        rows.append({
            "ticker": r.get("ticker"),
            "company": r.get("company"),
            "moat_score": r.get("moat_score"),
            # Scores
            "rivalry": forces.get("rivalry", {}).get("score"),
            "new_entrants": forces.get("new_entrants", {}).get("score"),
            "substitutes": forces.get("substitutes", {}).get("score"),
            "buyer_power": forces.get("buyer_power", {}).get("score"),
            "supplier_power": forces.get("supplier_power", {}).get("score"),
            # Rationale per forza
            "rivalry_why": forces.get("rivalry", {}).get("rationale", ""),
            "new_entrants_why": forces.get("new_entrants", {}).get("rationale", ""),
            "substitutes_why": forces.get("substitutes", {}).get("rationale", ""),
            "buyer_power_why": forces.get("buyer_power", {}).get("rationale", ""),
            "supplier_power_why": forces.get("supplier_power", {}).get("rationale", ""),
            # Sintesi
            "moat_summary": r.get("moat_summary", ""),
            "key_risks": " | ".join(r.get("key_risks", [])),
            "data_source": r.get("data_source", "10-K"),
            "date": r.get("analysis_date"),
        })
    df = pd.DataFrame(rows).sort_values("moat_score", ascending=False).reset_index(drop=True)
    df.index += 1
    return df

def print_detailed_report(results: list[dict]):
    """Stampa report narrativo dettagliato per ogni azienda."""
    sorted_results = sorted(
        [r for r in results if "forces" in r],
        key=lambda x: x.get("moat_score", 0),
        reverse=True
    )
    print(SCORE_LEGEND)
    print("=" * 70)
    print("DETAILED COMPANY ANALYSIS")
    print("=" * 70)

    for rank, r in enumerate(sorted_results, 1):
        forces = r["forces"]
        print(f"\n#{rank} {r['ticker']} — {r['company']}")
        print(f"    Overall Moat Score: {r.get('moat_score')} / 5")
        print(f"    {r.get('moat_summary', '')}")
        print(f"\n    Five Forces Breakdown:")
        for force in ["rivalry", "new_entrants", "substitutes", "buyer_power", "supplier_power"]:
            f = forces.get(force, {})
            print(f"      {force.upper()} [{f.get('score')}/5]: {f.get('rationale', '')}")
        risks = r.get("key_risks", [])
        if risks:
            print(f"\n    Key Risks / Threats:")
            for risk in risks:
                print(f"      ⚠ {risk}")
        print(f"\n    Source: {r.get('data_source')} | Date: {r.get('analysis_date')}")
        print("-" * 70)

def export_report():
    os.makedirs(DATA_OUTPUT, exist_ok=True)
    results = load_all_results()
    if not results:
        print("Nessun risultato trovato in data/output/")
        return None

    df = build_summary_df(results)

    # CSV completo
    csv_path = f"{DATA_OUTPUT}/porter_report.csv"
    df.to_csv(csv_path)
    print(f"CSV salvato in {csv_path}")

    # Report narrativo dettagliato
    print_detailed_report(results)

    # Tabella sintetica
    print("\nSUMMARY TABLE:")
    print(df[["ticker", "company", "moat_score", "rivalry", "new_entrants",
              "substitutes", "buyer_power", "supplier_power"]].to_string())
    return df

if __name__ == "__main__":
    export_report()
