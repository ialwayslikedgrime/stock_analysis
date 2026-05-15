from flask import Flask, render_template, jsonify
import json, glob, os, math

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_OUTPUT = os.path.join(BASE_DIR, "data", "output")

# Questa funzione "pulisce" i dati: trasforma i fastidiosi NaN di Python in None (che in JSON diventa null)
def clean_nans(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    return obj

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    all_data = {}
    search_pattern = os.path.join(DATA_OUTPUT, "*_investment.json")
    files = glob.glob(search_pattern)
    
    print(f"\n--- RICHIESTA API RICEVUTA ---")
    
    for inv_path in files:
        ticker = os.path.basename(inv_path).replace("_investment.json", "")
        fin_path = os.path.join(DATA_OUTPUT, f"{ticker}_financials.json")
        porter_path = os.path.join(DATA_OUTPUT, f"{ticker}_porter.json")
        
        if os.path.exists(fin_path) and os.path.exists(porter_path):
            try:
                with open(porter_path) as f: porter = json.load(f)
                with open(fin_path) as f: fin = json.load(f)
                with open(inv_path) as f: inv = json.load(f)
                
                if "error" not in inv:
                    all_data[ticker] = {"porter": porter, "financials": fin, "investment": inv}
            except Exception as e:
                print(f"⚠️ Errore lettura {ticker}: {e}")
    
    # Puliamo tutti i NaN prima di inviare i dati al browser!
    clean_data = clean_nans(all_data)
    
    print(f"✅ Dati puliti e inviati con successo per {len(clean_data)} aziende.")
    print(f"------------------------------\n")
    
    return jsonify(clean_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)