import os
import json
import time
import logging
import pandas as pd
from datetime import datetime
from config.settings import DATA_OUTPUT, DATA_RAW, DATA_PROCESSED

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(f"logs/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def load_progress() -> dict:
    """Carica lo stato del pipeline per resume automatico."""
    path = f"{DATA_OUTPUT}/pipeline_progress.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"completed": [], "failed": [], "skipped": []}

def save_progress(progress: dict):
    os.makedirs(DATA_OUTPUT, exist_ok=True)
    with open(f"{DATA_OUTPUT}/pipeline_progress.json", "w") as f:
        json.dump(progress, f, indent=2)

def is_done(ticker: str, stage: str) -> bool:
    """Controlla se uno stage è già completato per un ticker."""
    paths = {
        "10k":        f"{DATA_RAW}/{ticker}_10k.txt",
        "extract":    f"{DATA_PROCESSED}/{ticker}_qualitative.txt",
        "porter":     f"{DATA_OUTPUT}/{ticker}_porter.json",
        "financials": f"{DATA_OUTPUT}/{ticker}_financials.json",
        "investment": f"{DATA_OUTPUT}/{ticker}_investment.json",
    }
    return os.path.exists(paths.get(stage, ""))

def run_ticker(ticker: str, company: str, dry_run: bool = False) -> str:
    """
    Esegue il pipeline completo per un ticker.
    Ritorna: 'ok' | 'failed' | 'skipped'
    """
    from src.edgar import download_10k_text
    from src.extractor import process_ticker
    from src.analyzer import analyze_company
    from src.financials import get_financials
    from src.financial_analyzer import analyze as investment_analyze

    log.info(f"[{ticker}] Starting pipeline...")

    try:
        # Stage 1: Download 10-K
        if not is_done(ticker, "10k"):
            if dry_run:
                log.info(f"[{ticker}] DRY RUN: would download 10-K")
            else:
                text = download_10k_text(ticker)
                if not text:
                    log.warning(f"[{ticker}] 10-K download failed")
                    return "failed"
                time.sleep(0.5)
        else:
            log.info(f"[{ticker}] 10-K already downloaded")

        # Stage 2: Extract sections
        if not is_done(ticker, "extract"):
            if dry_run:
                log.info(f"[{ticker}] DRY RUN: would extract sections")
            else:
                result = process_ticker(ticker)
                if not result:
                    log.warning(f"[{ticker}] Extraction failed")
                    return "failed"
        else:
            log.info(f"[{ticker}] Extraction already done")

        # Stage 3: Porter analysis
        if not is_done(ticker, "porter"):
            if dry_run:
                log.info(f"[{ticker}] DRY RUN: would run Porter analysis")
            else:
                result = analyze_company(ticker, company)
                if not result or "error" in result:
                    log.warning(f"[{ticker}] Porter analysis failed")
                    return "failed"
                time.sleep(1)
        else:
            log.info(f"[{ticker}] Porter analysis already done")

        # Stage 4: Financials
        if not is_done(ticker, "financials"):
            if dry_run:
                log.info(f"[{ticker}] DRY RUN: would fetch financials")
            else:
                result = get_financials(ticker, years=5)
                if not result:
                    log.warning(f"[{ticker}] Financials failed")
                    return "failed"
                time.sleep(0.5)
        else:
            log.info(f"[{ticker}] Financials already done")

        # Stage 5: Investment analysis
        if not is_done(ticker, "investment"):
            if dry_run:
                log.info(f"[{ticker}] DRY RUN: would run investment analysis")
            else:
                result = investment_analyze(ticker)
                if not result or "error" in result:
                    log.warning(f"[{ticker}] Investment analysis failed")
                    return "failed"
                time.sleep(1)
        else:
            log.info(f"[{ticker}] Investment analysis already done")

        log.info(f"[{ticker}] ✓ Pipeline complete")
        return "ok"

    except Exception as e:
        log.error(f"[{ticker}] Exception: {e}", exc_info=True)
        return "failed"

def run_pipeline(
    tickers_df: pd.DataFrame,
    dry_run: bool = False,
    max_companies: int | None = None,
    resume: bool = True,
):
    """
    Esegue il pipeline su una lista di aziende.

    tickers_df: DataFrame con colonne [ticker, company, sector]
    dry_run: se True, non fa chiamate API reali
    max_companies: limita il numero di aziende (utile per test)
    resume: riprende da dove si era fermato
    """
    progress = load_progress() if resume else {"completed": [], "failed": [], "skipped": []}

    df = tickers_df.copy()
    if max_companies:
        df = df.head(max_companies)

    total = len(df)
    log.info(f"Pipeline starting: {total} companies | dry_run={dry_run} | resume={resume}")

    for i, row in df.iterrows():
        ticker  = row["ticker"]
        company = row["company"]
        sector  = row.get("sector", "Unknown")

        if ticker in progress["completed"]:
            log.info(f"[{ticker}] Already completed, skipping")
            continue

        log.info(f"Progress: {len(progress['completed'])}/{total} | [{ticker}] {company} ({sector})")

        status = run_ticker(ticker, company, dry_run=dry_run)

        if status == "ok":
            progress["completed"].append(ticker)
        elif status == "failed":
            progress["failed"].append(ticker)
        else:
            progress["skipped"].append(ticker)

        save_progress(progress)

        # Rate limiting tra aziende
        if not dry_run:
            time.sleep(2)

    log.info(f"\n{'='*50}")
    log.info(f"Pipeline complete!")
    log.info(f"  Completed: {len(progress['completed'])}")
    log.info(f"  Failed:    {len(progress['failed'])}")
    log.info(f"  Skipped:   {len(progress['skipped'])}")
    if progress["failed"]:
        log.info(f"  Failed tickers: {progress['failed']}")

    return progress

if __name__ == "__main__":
    from src.universe import get_sp500_tickers

    df = get_sp500_tickers()
    log.info(f"Loaded {len(df)} S&P 500 companies")

    # Test su 5 aziende di settori diversi prima di scalare
    test_sample = df.groupby("sector").first().reset_index()[["ticker","company","sector"]].head(10)
    log.info(f"Test sample:\n{test_sample.to_string()}")

    run_pipeline(
        test_sample,
        dry_run=False,
        resume=True,
    )
