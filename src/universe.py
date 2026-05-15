import pandas as pd
import requests
import io

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

def get_sp500_tickers() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(SP500_WIKI_URL, headers=headers)
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[0][["Symbol", "Security", "GICS Sector"]].copy()
    df.columns = ["ticker", "company", "sector"]
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    return df

if __name__ == "__main__":
    df = get_sp500_tickers()
    print(df.head(10))
    print(f"\nTotale aziende: {len(df)}")
