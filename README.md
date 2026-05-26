# CreditBridge Analytics — Universal Bank Statement Scorer

AI-powered credit scoring from Nigerian bank statements.

## Supported Banks
GTBank · Access Bank · Zenith Bank · First Bank · UBA · Fidelity Bank ·
Sterling Bank · Stanbic IBTC · Kuda · OPay · Moniepoint · PalmPay ·
FCMB · Polaris Bank · Wema Bank · Union Bank · Any Nigerian Bank (auto-fallback)

## How It Works
1. Upload a digital PDF bank statement (6–24 months)
2. Bank is auto-detected and the right parser is selected
3. 25 credit features are engineered from transaction history
4. A weighted model produces a 150–850 credit score
5. Balance is verified against statement header (tamper detection)

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Push this folder to a GitHub repo (public)
2. Go to share.streamlit.io → New app
3. Set main file path: `app.py`
4. Deploy — packages.txt installs poppler-utils automatically

## Files
- `app.py` — complete self-contained application
- `requirements.txt` — Python dependencies
- `packages.txt` — system package (poppler-utils for pdftotext)
- `.streamlit/config.toml` — dark theme configuration
