import json, os, glob, re

DATA_OUTPUT = "data/output"

def load_all_data():
    all_data = {}
    for porter_path in glob.glob(f"{DATA_OUTPUT}/*_porter.json"):
        ticker = os.path.basename(porter_path).replace("_porter.json", "")
        fin_path = f"{DATA_OUTPUT}/{ticker}_financials.json"
        inv_path = f"{DATA_OUTPUT}/{ticker}_investment.json"
        if not os.path.exists(fin_path) or not os.path.exists(inv_path):
            continue
        with open(porter_path) as f: porter = json.load(f)
        with open(fin_path) as f: fin = json.load(f)
        with open(inv_path) as f: inv = json.load(f)
        if "error" in inv or "forces" not in porter:
            continue
        all_data[ticker] = {"porter": porter, "financials": fin, "investment": inv}
    return all_data

def generate():
    all_data = load_all_data()
    if not all_data:
        print("No data found")
        return

    data_js = json.dumps(all_data, indent=2, ensure_ascii=True)

    with open("dashboard.html") as f:
        html = f.read()

    start = html.find("const RAW = ")
    end = html.find(";\n", start) + 2
    html = html[:start] + f"const RAW = {data_js};" + html[end:]

    with open("dashboard.html", "w") as f:
        f.write(html)

    print(f"✓ Dashboard updated: {len(all_data)} companies")
    print(f"  Tickers: {sorted(all_data.keys())}")

if __name__ == "__main__":
    generate()
