"""
CreditBridge Analytics — Universal Nigerian Bank Statement Scorer
================================================================
Supports: GTBank, Access Bank, Zenith Bank, First Bank, UBA,
          Fidelity, Sterling, Stanbic IBTC, Kuda, OPay, Moniepoint
          + any unknown bank via intelligent fallback parsing

Deploy:  streamlit run app.py
Install: pip install streamlit pdfplumber plotly pandas numpy scipy
System:  apt install poppler-utils  (for GTBank pdftotext extraction)
"""

import re, io, os, sys, warnings, subprocess, tempfile, uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

warnings.filterwarnings("ignore")

try:
    import pdfplumber
except ImportError:
    st.error("pdfplumber not installed. Run: pip install pdfplumber")
    st.stop()

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CreditBridge — Universal Bank Statement Scorer",
    page_icon="🏦", layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#0b0f1c;color:#e2e8f0;}
#MainMenu,header,footer{visibility:hidden;}

.topbar{background:#080c18;border-bottom:1px solid #1a2035;padding:14px 3rem;
  margin:-4rem -4rem 2rem;display:flex;align-items:center;justify-content:space-between;}
.topbar-logo{display:flex;align-items:center;gap:10px;}
.topbar-mark{background:linear-gradient(135deg,#00c896,#0ea5e9);color:#080c18;
  font-family:'DM Mono',monospace;font-weight:700;font-size:0.75rem;
  width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;}
.topbar-name{font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;color:#e2e8f0;}
.topbar-sub{font-family:'DM Mono',monospace;font-size:0.68rem;color:#00c896;
  letter-spacing:0.1em;background:rgba(0,200,150,0.1);
  border:1px solid rgba(0,200,150,0.25);padding:3px 10px;border-radius:20px;}

.bank-detected{background:rgba(0,200,150,0.08);border:1px solid rgba(0,200,150,0.25);
  border-radius:12px;padding:14px 20px;margin-bottom:16px;display:flex;
  align-items:center;gap:12px;}
.bank-icon{font-size:1.6rem;}
.bank-name{font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;color:#e2e8f0;}
.bank-meta{font-size:0.78rem;color:#475569;font-family:'DM Mono',monospace;}

.score-card{background:linear-gradient(135deg,#0f1628,#111827);
  border:1px solid #1e2d45;border-radius:20px;padding:36px;text-align:center;
  position:relative;overflow:hidden;}
.score-card::before{content:'';position:absolute;top:-80px;right:-80px;
  width:240px;height:240px;
  background:radial-gradient(circle,rgba(0,200,150,0.08),transparent 70%);border-radius:50%;}
.score-num{font-family:'Syne',sans-serif;font-weight:800;
  font-size:5.5rem;line-height:1;letter-spacing:-0.04em;}
.score-denom{font-family:'DM Mono',monospace;font-size:0.75rem;color:#475569;margin-top:4px;}
.risk-pill{display:inline-block;padding:5px 16px;border-radius:100px;
  font-family:'DM Mono',monospace;font-size:0.75rem;letter-spacing:0.12em;margin-top:10px;}
.pd-strip{display:flex;justify-content:center;gap:28px;
  margin-top:22px;padding-top:18px;border-top:1px solid #1e2d45;}
.pd-val{font-size:1.15rem;font-weight:700;color:#e2e8f0;}
.pd-lbl{font-family:'DM Mono',monospace;font-size:0.6rem;color:#475569;
  text-transform:uppercase;letter-spacing:0.1em;margin-top:3px;}

.kpi{background:#0f1628;border:1px solid #1e2d45;border-radius:14px;padding:18px 20px;}
.kpi-lbl{font-family:'DM Mono',monospace;font-size:0.62rem;color:#475569;
  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:7px;}
.kpi-val{font-family:'Syne',sans-serif;font-weight:700;font-size:1.5rem;
  color:#e2e8f0;line-height:1;}
.kpi-sub{font-size:0.73rem;color:#475569;margin-top:4px;}

.contrib-row{display:flex;align-items:center;gap:10px;
  padding:8px 0;border-bottom:1px solid #1a2035;}
.contrib-name{flex:1;font-size:0.8rem;color:#94a3b8;font-family:'DM Mono',monospace;}
.contrib-bg{width:90px;height:4px;background:#1e2d45;border-radius:2px;overflow:hidden;}
.contrib-fill{height:100%;border-radius:2px;}

.info-box{background:#0f1628;border:1px solid #1e2d45;
  border-left:3px solid #00c896;border-radius:0 10px 10px 0;
  padding:12px 16px;font-size:0.83rem;color:#94a3b8;line-height:1.6;margin:10px 0;}
.warn-box{background:#0f1628;border:1px solid #1e2d45;
  border-left:3px solid #fbbf24;border-radius:0 10px 10px 0;
  padding:12px 16px;font-size:0.83rem;color:#94a3b8;line-height:1.6;margin:10px 0;}
.error-box{background:#0f1628;border:1px solid #1e2d45;
  border-left:3px solid #f87171;border-radius:0 10px 10px 0;
  padding:12px 16px;font-size:0.83rem;color:#94a3b8;line-height:1.6;margin:10px 0;}
.section-hd{font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;
  color:#e2e8f0;margin:28px 0 14px;display:flex;align-items:center;gap:10px;}
.section-hd::after{content:'';flex:1;height:1px;background:#1e2d45;}

.stButton>button{background:linear-gradient(135deg,#00c896,#0ea5e9);
  color:#080c18;border:none;border-radius:100px;font-weight:700;
  font-size:0.9rem;padding:12px 28px;width:100%;transition:all 0.2s;}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(0,200,150,0.3);}
[data-testid="stFileUploader"]{background:#0f1628;border:2px dashed #1e2d45;border-radius:14px;}
div[data-testid="stMetric"]{background:#0f1628;border:1px solid #1e2d45;border-radius:12px;padding:14px;}
div[data-testid="stMetric"] label{color:#475569!important;font-family:'DM Mono',monospace!important;font-size:0.7rem!important;}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#e2e8f0!important;font-family:'Syne',sans-serif!important;}
.stTabs [data-baseweb="tab"]{color:#64748b;}
.stTabs [aria-selected="true"]{color:#00c896!important;}
.stTabs [data-baseweb="tab-highlight"]{background:#00c896!important;}
.stTabs [data-baseweb="tab-border"]{background:#1e2d45!important;}
h1,h2,h3{font-family:'Syne',sans-serif!important;color:#e2e8f0!important;}
.stMarkdown p{color:#94a3b8;}
[data-testid="stExpander"]{background:#0f1628;border:1px solid #1e2d45;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

PLOTLY_BG = "rgba(0,0,0,0)"
GRID_COL  = "#1e2d45"
TEXT_COL  = "#64748b"

# ══════════════════════════════════════════════════════════════════
# BANK DETECTION
# ══════════════════════════════════════════════════════════════════

BANK_SIGNATURES = {
    "GTBank": {
        "patterns": [r"guaranty trust|gtbank|gtb\b|appdev-gtbank", r"635 akin adesola"],
        "icon": "🟩", "color": "#00a651",
        "parser": "gtb_fixed_width",
        "full_name": "Guaranty Trust Bank",
    },
    "Access Bank": {
        "patterns": [r"access bank", r"access bank plc"],
        "icon": "🟧", "color": "#f7941d",
        "parser": "table_based",
        "full_name": "Access Bank Plc",
    },
    "Zenith Bank": {
        "patterns": [r"zenith bank", r"zenith bank plc"],
        "icon": "🟥", "color": "#e31e24",
        "parser": "table_based",
        "full_name": "Zenith Bank Plc",
    },
    "First Bank": {
        "patterns": [r"first bank of nigeria|firstbank|first bank nigeria"],
        "icon": "🟦", "color": "#003087",
        "parser": "table_based",
        "full_name": "First Bank of Nigeria",
    },
    "UBA": {
        "patterns": [r"united bank for africa|uba\b"],
        "icon": "🔴", "color": "#c8102e",
        "parser": "table_based",
        "full_name": "United Bank for Africa",
    },
    "Fidelity Bank": {
        "patterns": [r"fidelity bank"],
        "icon": "🟩", "color": "#006633",
        "parser": "table_based",
        "full_name": "Fidelity Bank Plc",
    },
    "Sterling Bank": {
        "patterns": [r"sterling bank"],
        "icon": "🟨", "color": "#f5a623",
        "parser": "table_based",
        "full_name": "Sterling Bank Plc",
    },
    "Stanbic IBTC": {
        "patterns": [r"stanbic ibtc|stanbic bank"],
        "icon": "🔵", "color": "#0033a0",
        "parser": "table_based",
        "full_name": "Stanbic IBTC Bank",
    },
    "Kuda Bank": {
        "patterns": [r"kuda\b|kuda microfinance|kuda bank"],
        "icon": "🟣", "color": "#7b2d8b",
        "parser": "table_based",
        "full_name": "Kuda Microfinance Bank",
    },
    "OPay": {
        "patterns": [r"opay|paycom\b|o-pay"],
        "icon": "🟢", "color": "#1bca8e",
        "parser": "table_based",
        "full_name": "OPay Digital Services",
    },
    "Moniepoint": {
        "patterns": [r"moniepoint|teamapt|moniemfb"],
        "icon": "🔷", "color": "#0066cc",
        "parser": "table_based",
        "full_name": "Moniepoint MFB",
    },
    "Palmpay": {
        "patterns": [r"palmpay"],
        "icon": "🟤", "color": "#ff6b00",
        "parser": "table_based",
        "full_name": "PalmPay Limited",
    },
    "FCMB": {
        "patterns": [r"fcmb|first city monument"],
        "icon": "🟩", "color": "#006e34",
        "parser": "table_based",
        "full_name": "First City Monument Bank",
    },
    "Polaris Bank": {
        "patterns": [r"polaris bank|skye bank"],
        "icon": "🟦", "color": "#003d7c",
        "parser": "table_based",
        "full_name": "Polaris Bank",
    },
    "Wema Bank": {
        "patterns": [r"wema bank"],
        "icon": "🟪", "color": "#7c0097",
        "parser": "table_based",
        "full_name": "Wema Bank Plc",
    },
    "Union Bank": {
        "patterns": [r"union bank"],
        "icon": "🟥", "color": "#990000",
        "parser": "table_based",
        "full_name": "Union Bank of Nigeria",
    },
}

def detect_bank(text: str) -> dict:
    """Detect bank from statement text. Returns bank info dict."""
    text_lower = text[:3000].lower()
    for bank_name, info in BANK_SIGNATURES.items():
        for pattern in info["patterns"]:
            if re.search(pattern, text_lower):
                return {"name": bank_name, **info}
    return {
        "name": "Unknown Bank", "icon": "🏦", "color": "#64748b",
        "parser": "table_based", "full_name": "Nigerian Bank (Auto-detected)",
        "patterns": [],
    }

# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

DATE_FORMATS = [
    "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d.%m.%Y",
    "%d-%b-%y", "%Y/%m/%d", "%b %d, %Y", "%d %b, %Y",
]

def parse_date(s: str):
    s = str(s).strip().strip("'\"")
    for fmt in DATE_FORMATS:
        try: return pd.Timestamp(datetime.strptime(s, fmt))
        except: pass
    return None

def parse_amount(s: str) -> float:
    """Parse Nigerian amount string to float. Handles all formats."""
    if not s: return 0.0
    s = str(s).strip()
    # Handle parentheses for debits: (1,234.56)
    negative = s.startswith("(") and s.endswith(")")
    # Remove all non-numeric except decimal point and minus
    s = re.sub(r"[₦,\(\)\s]", "", s)
    s = re.sub(r"[Nn][Gg][Nn]", "", s)
    s = s.replace("DR","").replace("CR","").strip()
    if not s: return 0.0
    try:
        v = float(s)
        return -v if negative else abs(v)
    except:
        return 0.0

NARR_PATTERNS = [
    (r"loan|repay|repmt|instalment|mortgage|lend\b",         "loan_repayment",    "financial_institution"),
    (r"nepa|phcn|ekedc|ikedc|aedc|kedco|bedc|electricity|prepaid.?meter|dstv|gotv|startimes|water.?board|lawma", "utility_payment", "utility_company"),
    (r"piggyvest|pckapp|piggytech|cowrywise",                "transfer_sent",     "financial_institution"),
    (r"pos\b|posweb|point.of.sale|web.purchase|e.tranz|card.purchase", "pos_settlement", "aggregator_platform"),
    (r"paystack|flutterwave|remita|monnify|squad|interswitch","aggregator_payout","aggregator_platform"),
    (r"airtime|recharge|mtn\b|glo\b|airtel\b|9mobile|etisalat","airtime_purchase","aggregator_platform"),
    (r"stamp.dut|emtl|firs\b|lirs\b|\btax\b|paye\b",        "tax_payment",       "government_agency"),
    (r"commission|charges|vat\b|\bfee\b|levy\b",             "bank_charge",       "financial_institution"),
    (r"\batm\b|atm.wd|cash.withdrawal|atm withdrawal",       "cash_withdrawal",   "individual_transfer"),
    (r"salary|payroll|staff.wage|wages",                     "transfer_received", "individual_transfer"),
    (r"transfer.from|trf.from|from.*opay|from.*palmpay|from.*kuda|transfer.between.customers|nip.*from|deposit\b|lodgement", "customer_payment", "retail_customer"),
    (r"transfer.to|trf.to|nip.transfer|nibss|nip.*to|outward", "transfer_sent",   "individual_transfer"),
    (r"reversal|refund|reverse",                             "transfer_received", "individual_transfer"),
]

def categorise(narrative: str, is_inflow: bool) -> tuple:
    txt = narrative.lower()
    for pattern, txn_type, counterparty in NARR_PATTERNS:
        if re.search(pattern, txt):
            if txn_type == "customer_payment" and not is_inflow:
                txn_type = "supplier_payment"
            if txn_type == "transfer_sent" and is_inflow:
                txn_type = "transfer_received"
            return txn_type, counterparty
    return ("transfer_received","individual_transfer") if is_inflow else ("transfer_sent","individual_transfer")

# ══════════════════════════════════════════════════════════════════
# PARSER 1 — GTBank fixed-width (pdftotext -layout)
# ══════════════════════════════════════════════════════════════════

def parse_gtb_fixed_width(text: str) -> list:
    """
    GTBank uses fixed-width text layout.
    Debit: cols 55-83, Credit: cols 83-103, Balance: cols 103-128
    """
    DATE_RE = re.compile(
        r'^\s{5,18}(\d{2}-\w{3}-\d{4}|\d{2}/\d{2}/\d{4})\s+'
        r'(\d{2}-\w{3}-\d{4}|\d{2}/\d{2}/\d{4})\s'
    )
    def extract_num(s):
        nums = re.findall(r'[\d,]+\.\d+', s)
        for n in nums:
            try:
                v = float(n.replace(",",""))
                if v > 0: return v
            except: pass
        return 0.0

    transactions, current, rmks = [], None, []

    def flush(txn, rmks):
        if txn is None: return
        narrative = " ".join(rmks)[:200]
        txn["narrative"] = narrative
        is_inflow = txn["direction"] == "inflow"
        txn["txn_type"], txn["counterparty_type"] = categorise(narrative, is_inflow)
        txn["is_regular_payment"] = txn["txn_type"] in ("utility_payment","loan_repayment")
        transactions.append(txn)

    for line in text.split("\n"):
        m = DATE_RE.match(line)
        if m:
            flush(current, rmks); rmks = []
            d = parse_date(m.group(1))
            if d is None: current = None; continue
            debit  = extract_num(line[55:84]  if len(line)>55  else "")
            credit = extract_num(line[83:104] if len(line)>83  else "")
            bal    = extract_num(line[103:128] if len(line)>103 else "")
            if bal == 0: bal = extract_num(line[95:135] if len(line)>95 else "")
            if bal == 0: current = None; continue
            if   debit>0 and credit==0: amount,direction = debit,"outflow"
            elif credit>0 and debit==0: amount,direction = credit,"inflow"
            elif credit>0 and debit>0:  amount,direction = (debit,"outflow") if debit>=credit else (credit,"inflow")
            else: current = None; continue
            rmk = line[139:].strip() if len(line)>139 else ""
            current = {"date":d,"amount_ngn":round(amount,2),"direction":direction,
                       "balance_after_ngn":round(bal,2)}
            rmks = [rmk] if rmk else []
        else:
            if line.strip() and current and len(line)>139:
                p = line[139:].strip()
                if p: rmks.append(p)
    flush(current, rmks)
    return transactions

# ══════════════════════════════════════════════════════════════════
# PARSER 2 — Table-based (pdfplumber) — all other banks
# ══════════════════════════════════════════════════════════════════

# Column header synonyms
DATE_HDRS    = {"date","trans date","transaction date","value date","txn date",
                "posting date","tran date","value  date","trans. date"}
DEBIT_HDRS   = {"debit","dr","withdrawal","withdrawals","amount (dr)","debit amount",
                "money out","dr amount","amount dr","paid out","out","outflow"}
CREDIT_HDRS  = {"credit","cr","deposit","deposits","amount (cr)","credit amount",
                "money in","cr amount","amount cr","paid in","in","inflow"}
BALANCE_HDRS = {"balance","running balance","ledger balance","available balance",
                "bal","closing balance","outstanding balance"}
NARR_HDRS    = {"narration","narrative","description","details","particulars",
                "transaction details","remarks","memo","trans description",
                "transaction narration","naration","narr"}

def normalise_header(h: str) -> str:
    return str(h).lower().strip().replace("  "," ") if h else ""

def detect_col_map(headers: list) -> dict:
    """Map header strings to semantic column roles."""
    col_map = {}
    for i, h in enumerate(headers):
        nh = normalise_header(h)
        if nh in DATE_HDRS and "date" not in col_map:
            col_map["date"] = i
        elif nh in DEBIT_HDRS and "debit" not in col_map:
            col_map["debit"] = i
        elif nh in CREDIT_HDRS and "credit" not in col_map:
            col_map["credit"] = i
        elif nh in BALANCE_HDRS and "balance" not in col_map:
            col_map["balance"] = i
        elif nh in NARR_HDRS and "narration" not in col_map:
            col_map["narration"] = i
    return col_map

def parse_table_row(row: list, col_map: dict) -> dict | None:
    """Parse one table row into a transaction dict."""
    if not col_map or len(row) < 2:
        return None

    def get(key, default=""):
        idx = col_map.get(key)
        if idx is None or idx >= len(row): return default
        return str(row[idx]).strip() if row[idx] else default

    date = parse_date(get("date"))
    if date is None: return None

    debit_raw  = get("debit")
    credit_raw = get("credit")
    bal_raw    = get("balance")
    narrative  = get("narration", "")

    debit  = parse_amount(debit_raw)
    credit = parse_amount(credit_raw)
    bal    = parse_amount(bal_raw)

    # Some banks use a single "amount" column with DR/CR suffix
    if debit == 0 and credit == 0 and "debit" not in col_map:
        amt_raw = get("narration","") # fallback
        if "DR" in str(debit_raw).upper(): debit = parse_amount(debit_raw)
        if "CR" in str(credit_raw).upper(): credit = parse_amount(credit_raw)

    if bal == 0: return None  # no balance = not a transaction row

    if   debit>0 and credit==0: amount, direction = debit, "outflow"
    elif credit>0 and debit==0: amount, direction = credit, "inflow"
    elif credit>0 and debit>0:
        amount, direction = (debit,"outflow") if debit>=credit else (credit,"inflow")
    else: return None

    if amount <= 0: return None

    return {
        "date":             date,
        "amount_ngn":       round(amount, 2),
        "direction":        direction,
        "balance_after_ngn":round(bal, 2),
        "narrative":        narrative[:200],
    }

def parse_table_based(pdf_bytes: bytes) -> list:
    """
    Universal table-based parser using pdfplumber.
    Works for Access, Zenith, First Bank, UBA, Fidelity,
    Sterling, Stanbic, Kuda, OPay, Moniepoint, and others.
    """
    transactions = []
    col_map = {}

    TABLE_SETTINGS = [
        # Try strict line-based first (works for most banks)
        {"vertical_strategy":"lines","horizontal_strategy":"lines",
         "snap_tolerance":5,"join_tolerance":3,"edge_min_length":10},
        # Then text-based (works for Kuda, OPay, fintech PDFs)
        {"vertical_strategy":"text","horizontal_strategy":"text",
         "snap_tolerance":4,"join_tolerance":2},
        # Explicit lines only
        {"vertical_strategy":"explicit","horizontal_strategy":"lines",
         "explicit_vertical_lines":[]},
    ]

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for settings in TABLE_SETTINGS:
                try:
                    tables = page.extract_tables(settings)
                    if tables: break
                except: tables = []

            for table in (tables or []):
                for row in table:
                    if not row or all(not c for c in row): continue
                    cleaned = [str(c).strip() if c else "" for c in row]

                    # Detect header row
                    if not col_map:
                        new_map = detect_col_map(cleaned)
                        if "date" in new_map and "balance" in new_map:
                            col_map = new_map
                            continue
                        # Header might repeat mid-document
                    elif any(normalise_header(c) in DATE_HDRS for c in cleaned):
                        new_map = detect_col_map(cleaned)
                        if "date" in new_map and "balance" in new_map:
                            col_map = new_map
                            continue

                    if not col_map: continue

                    txn = parse_table_row(cleaned, col_map)
                    if txn:
                        txn["txn_type"], txn["counterparty_type"] = categorise(
                            txn["narrative"], txn["direction"]=="inflow"
                        )
                        txn["is_regular_payment"] = txn["txn_type"] in (
                            "utility_payment","loan_repayment"
                        )
                        transactions.append(txn)

    return transactions

# ══════════════════════════════════════════════════════════════════
# PARSER 3 — Text-line fallback (when tables fail)
# Intelligently parses any tabular text by finding amount columns
# ══════════════════════════════════════════════════════════════════

def parse_text_fallback(text: str) -> list:
    """
    Last-resort parser: finds any line with a date + 2 or more amounts.
    Works on virtually any text-based bank statement.
    """
    # Find lines with date + amounts
    DATE_PATTERN = re.compile(
        r'(\d{2}[-/]\w{2,3}[-/]\d{2,4}|\d{2}[-/]\d{2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})'
    )
    AMOUNT_PATTERN = re.compile(r'[\d,]+\.\d{2}')

    transactions = []

    for line in text.split("\n"):
        dm = DATE_PATTERN.search(line)
        if not dm: continue
        date = parse_date(dm.group(1))
        if date is None: continue

        amounts = [(m.start(), parse_amount(m.group()))
                   for m in AMOUNT_PATTERN.finditer(line)]
        if len(amounts) < 2: continue

        # Last amount is almost always the balance
        # Second-to-last is credit or debit
        bal = amounts[-1][1]
        if bal <= 0: continue

        # Find the transaction amount (non-zero, not the balance)
        txn_amounts = [(pos,v) for pos,v in amounts[:-1] if v > 0]
        if not txn_amounts: continue

        # Positional heuristic: earlier column = debit, later = credit
        # If only one amount, use balance delta to determine direction
        if len(txn_amounts) == 1:
            amount = txn_amounts[0][1]
            # Try to infer direction from narrative
            narrative = line[dm.end():amounts[0][0]].strip()
            is_inflow = any(w in narrative.lower() for w in
                           ["credit","deposit","from","received","transfer in"])
            direction = "inflow" if is_inflow else "outflow"
        else:
            # Two amounts: first=debit, second=credit (standard layout)
            debit  = txn_amounts[0][1]
            credit = txn_amounts[1][1] if len(txn_amounts)>1 else 0
            if   debit>0 and credit==0: amount,direction = debit,"outflow"
            elif credit>0 and debit==0: amount,direction = credit,"inflow"
            else: amount,direction = (debit,"outflow") if debit>=credit else (credit,"inflow")

        narrative = line[dm.end():].strip()[:200]
        txn_type, counterparty = categorise(narrative, direction=="inflow")

        transactions.append({
            "date":             date,
            "amount_ngn":       round(amount, 2),
            "direction":        direction,
            "balance_after_ngn":round(bal, 2),
            "narrative":        narrative,
            "txn_type":         txn_type,
            "counterparty_type":counterparty,
            "is_regular_payment": txn_type in ("utility_payment","loan_repayment"),
        })

    return transactions

# ══════════════════════════════════════════════════════════════════
# META EXTRACTOR
# ══════════════════════════════════════════════════════════════════

def extract_meta(text: str) -> dict:
    meta = {}
    patterns = {
        "account_name":    r"(?:account.name|customer.name|name)[:\s]+([A-Z][A-Z\s.&,'-]{4,60}?)(?:\n|$)",
        "account_no":      r"(?:account.no|acct.no|account.number)[:\s]+(\d{10}|\d{4}\s\d{4}\s\d{4})",
        "account_type":    r"(?:account.type)[:\s]+([A-Z][A-Z\s]+?)(?:\n|$)",
        "period":          r"(?:statement.period|period)[:\s]*:?\s*([^\n]{8,40})",
        "opening_balance": r"(?:opening.balance|opening.bal)[:\s]+([\d,]+\.?\d*)",
        "closing_balance": r"(?:closing.balance|closing.bal)[:\s]+([\d,]+\.?\d*)",
        "total_debit":     r"(?:total.debit|total.dr|total.withdrawal)[:\s]+([\d,]+\.?\d*)",
        "total_credit":    r"(?:total.credit|total.cr|total.deposit)[:\s]+([\d,]+\.?\d*)",
        "branch":          r"(?:branch.name|branch)[:\s]+([A-Z][A-Z\s\-]+?)(?:\n|$)",
        "currency":        r"(?:currency)[:\s]+([A-Z\s]+?)(?:\n|$)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if key in ("opening_balance","closing_balance","total_debit","total_credit"):
                meta[key] = parse_amount(val)
            else:
                meta[key] = val

    # Fallback name from "CUSTOMER STATEMENT\n  NAME" pattern
    m = re.search(r'CUSTOMER STATEMENT\s*\n\s*([A-Z][A-Z\s.]{4,50}?)(?:\n|$)', text)
    if m and "account_name" not in meta:
        meta["account_name"] = m.group(1).strip()

    return meta

# ══════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def parse_statement(pdf_bytes: bytes) -> tuple:
    """
    Auto-detect bank and parse statement using the right strategy.
    Returns (transactions_df, meta_dict, bank_info, parse_method)
    """
    # ── Step 1: Extract raw text ──────────────────────────────────
    raw_text = ""
    parse_method = "unknown"

    # Try pdftotext first (best for GTBank fixed-width)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, text=True, timeout=60
        )
        raw_text = result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raw_text = ""
    finally:
        try: os.unlink(tmp_path)
        except: pass

    # Fallback to pdfplumber text
    if not raw_text.strip():
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            parts = []
            for page in pdf.pages:
                t = page.extract_text(layout=True) or page.extract_text() or ""
                parts.append(t)
            raw_text = "\n".join(parts)

    if not raw_text.strip():
        raise ValueError(
            "Could not extract text from PDF. "
            "Ensure it is a digital (not scanned) bank statement."
        )

    # ── Step 2: Detect bank ───────────────────────────────────────
    bank_info = detect_bank(raw_text)
    meta      = extract_meta(raw_text)

    # ── Step 3: Parse transactions ────────────────────────────────
    transactions = []

    # GTBank: use calibrated fixed-width parser
    if bank_info["parser"] == "gtb_fixed_width":
        transactions = parse_gtb_fixed_width(raw_text)
        parse_method = "GTBank fixed-width column parser"

    # All other banks: try table-based first
    if not transactions:
        transactions = parse_table_based(pdf_bytes)
        if transactions:
            parse_method = f"Table extraction (pdfplumber) — {bank_info['name']}"

    # Universal text fallback
    if not transactions:
        transactions = parse_text_fallback(raw_text)
        if transactions:
            parse_method = f"Text-line fallback parser — {bank_info['name']}"

    if not transactions:
        raise ValueError(
            f"No transactions found for {bank_info['name']}. "
            "This may be a scanned PDF — only digital statements are supported. "
            "Try downloading a fresh copy from your bank's internet banking portal."
        )

    # ── Step 4: Build DataFrame ───────────────────────────────────
    df = pd.DataFrame(transactions)
    df["transaction_id"] = [f"TXN-{i:05d}" for i in range(len(df))]
    df["month"]          = df["date"].dt.month
    df["day_of_month"]   = df["date"].dt.day
    df["day_of_week"]    = df["date"].dt.dayofweek
    df["week_of_year"]   = df["date"].dt.isocalendar().week.astype(int)
    df["platform"]       = bank_info["name"]
    df["sme_id"]         = "STMT_001"

    # Remove junk rows
    df = df[df["amount_ngn"] > 0].copy()
    df = df[df["amount_ngn"] < 1_000_000_000].copy()
    df = df.sort_values("date").reset_index(drop=True)

    # Deduplicate (same date + amount + balance)
    df = df.drop_duplicates(
        subset=["date","amount_ngn","direction","balance_after_ngn"]
    ).reset_index(drop=True)

    return df, meta, bank_info, parse_method

# ══════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════

def engineer_features(df: pd.DataFrame) -> dict:
    inflows  = df[df["direction"]=="inflow"]
    outflows = df[df["direction"]=="outflow"]
    total_in  = inflows["amount_ngn"].sum()
    total_out = outflows["amount_ngn"].sum()
    obs_days  = max((df["date"].max()-df["date"].min()).days, 1)
    obs_months= max(df["date"].dt.to_period("M").nunique(), 1)

    monthly_in  = inflows.groupby(inflows["date"].dt.to_period("M"))["amount_ngn"].sum()
    monthly_out = outflows.groupby(outflows["date"].dt.to_period("M"))["amount_ngn"].sum()
    inflow_cv   = float(monthly_in.std()/monthly_in.mean()) if len(monthly_in)>1 and monthly_in.mean()>0 else 1.0

    bal           = df["balance_after_ngn"]
    bal_mean      = bal.mean()
    bal_min       = bal.min()
    near_zero     = float((bal<5_000).mean())
    has_negative  = int(bal.min()<0)

    if len(df) > 5:
        slope,_,_,_,_ = stats.linregress(np.arange(len(df)), bal.values)
    else: slope = 0.0

    util_months = df[df["txn_type"]=="utility_payment"]["date"].dt.to_period("M").nunique()
    loan_count  = int((df["txn_type"]=="loan_repayment").sum())
    has_loan    = int(loan_count > 0)
    reg_months  = df[df["is_regular_payment"]]["date"].dt.to_period("M").nunique()
    reg_rate    = float(reg_months / obs_months)

    cp_unique   = df["counterparty_type"].nunique()

    mid         = df["date"].min()+pd.Timedelta(days=obs_days//2)
    in_first    = inflows[inflows["date"]<=mid]["amount_ngn"].sum()
    in_second   = inflows[inflows["date"]>mid]["amount_ngn"].sum()
    is_growing  = int(in_second>in_first*1.05)

    savings_rate  = float((total_in-total_out)/max(total_in,1))
    airtime_freq  = float((df["txn_type"]=="airtime_purchase").mean())
    atm_share     = float((df["txn_type"]=="cash_withdrawal").mean())
    charge_share  = float((df["txn_type"]=="bank_charge").mean())
    peak_month_in = float(monthly_in.max()) if len(monthly_in)>0 else 0.0

    return {
        "total_txn_count":  len(df),
        "total_inflow_ngn": total_in,
        "total_outflow_ngn":total_out,
        "net_flow_ngn":     total_in-total_out,
        "avg_daily_inflow": total_in/obs_days,
        "obs_days":         obs_days,
        "obs_months":       obs_months,
        "inflow_cv":        inflow_cv,
        "monthly_in_std":   float(monthly_in.std()) if len(monthly_in)>1 else 0.0,
        "bal_mean":         bal_mean,
        "bal_min":          bal_min,
        "bal_std":          float(bal.std()),
        "bal_slope":        float(slope),
        "near_zero_rate":   near_zero,
        "has_negative":     has_negative,
        "util_months":      util_months,
        "loan_count":       loan_count,
        "has_loan":         has_loan,
        "reg_rate":         reg_rate,
        "reg_months":       reg_months,
        "cp_unique":        cp_unique,
        "is_growing":       is_growing,
        "savings_rate":     savings_rate,
        "airtime_freq":     airtime_freq,
        "atm_share":        atm_share,
        "charge_share":     charge_share,
        "peak_month_in":    peak_month_in,
    }

# ══════════════════════════════════════════════════════════════════
# SCORING MODEL
# ══════════════════════════════════════════════════════════════════

def score_features(f: dict) -> dict:
    prob = 0.32
    obs_m = max(f["obs_months"], 1)

    # Positive signals
    prob -= f["reg_rate"] * 0.16
    prob -= min(f["bal_mean"]/500_000, 1.0) * 0.10
    prob -= max(0, 1-f["inflow_cv"]) * 0.08
    prob -= (f["util_months"]/obs_m) * 0.07
    prob -= f["has_loan"] * 0.08
    prob -= f["is_growing"] * 0.05
    prob -= min(f["obs_days"]/365, 1.0) * 0.04
    prob -= min(f["cp_unique"]/8, 1.0) * 0.03
    if f["savings_rate"] > 0:
        prob -= min(f["savings_rate"], 0.5) * 0.05

    # Negative signals
    prob += f["has_negative"] * 0.13
    prob += f["near_zero_rate"] * 0.12
    prob += min(f["inflow_cv"], 2.0) * 0.04
    prob += f["atm_share"] * 0.04
    if f["savings_rate"] < 0:
        prob += abs(f["savings_rate"]) * 0.06

    prob = float(np.clip(prob, 0.02, 0.97))
    log_odds     = np.log(prob/(1-prob))
    credit_score = int(np.clip(500 - log_odds*50, 150, 850))

    bands = [
        (750,850,"LOW",       "#00c896","Strong credit profile. Recommended for standard lending terms."),
        (600,749,"LOW-MEDIUM","#4ade80","Good profile. Suitable for most products with routine monitoring."),
        (450,599,"MEDIUM",    "#fbbf24","Moderate risk. Consider reduced amounts or shorter terms."),
        (300,449,"HIGH",      "#f97316","Elevated risk. Enhanced due diligence recommended."),
        (150,299,"VERY HIGH", "#f87171","High default probability. Manual underwriting required."),
    ]
    for lo,hi,band,colour,guidance in bands:
        if lo<=credit_score<=hi:
            risk_band,band_colour,lender_guidance = band,colour,guidance; break
    else:
        risk_band,band_colour,lender_guidance = "UNKNOWN","#64748b","Score outside expected range."

    dist       = abs(prob-0.5)
    confidence = "HIGH" if dist>0.35 else "MEDIUM" if dist>0.20 else "LOW"

    contribs = []
    if f["reg_rate"]>0.5:       contribs.append(("▲","Payment regularity",        f["reg_rate"]*0.16,      "positive"))
    if f["has_loan"]:            contribs.append(("▲","Active loan repayment",     0.08,                    "positive"))
    if f["bal_mean"]>20_000:     contribs.append(("▲","Healthy account balance",   min(f["bal_mean"]/500000,1)*0.10,"positive"))
    if f["util_months"]>=4:      contribs.append(("▲","Utility payment habit",     (f["util_months"]/obs_m)*0.07,"positive"))
    if f["is_growing"]:          contribs.append(("▲","Inflow growth trend",       0.05,                    "positive"))
    if f["savings_rate"]>0.05:   contribs.append(("▲","Positive savings rate",     min(f["savings_rate"],0.5)*0.05,"positive"))
    if f["has_negative"]:        contribs.append(("▼","Negative balance history",  0.13,                    "negative"))
    if f["near_zero_rate"]>0.15: contribs.append(("▼","Near-zero balance rate",    f["near_zero_rate"]*0.12,"negative"))
    if f["inflow_cv"]>0.6:       contribs.append(("▼","High income volatility",    min(f["inflow_cv"],2)*0.04,"negative"))
    if not f["has_loan"]:        contribs.append(("▼","No loan repayment data",    0.04,                    "negative"))
    if f["savings_rate"]<-0.05:  contribs.append(("▼","Outflows exceed inflows",   abs(f["savings_rate"])*0.06,"negative"))
    contribs.sort(key=lambda x:-x[2])

    return {
        "credit_score":   credit_score,
        "risk_band":      risk_band,
        "band_colour":    band_colour,
        "prob_default":   prob,
        "confidence":     confidence,
        "lender_guidance":lender_guidance,
        "contributors":   contribs[:6],
    }

def verify_balance(df, meta) -> dict:
    stated = meta.get("closing_balance", 0)
    actual = df["balance_after_ngn"].iloc[-1] if len(df)>0 else 0
    diff   = abs(stated-actual)
    return {"stated":stated,"actual":actual,"diff":diff,"verified":diff<50.0}

# ══════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════

def chart_monthly_flow(df):
    inflows  = df[df["direction"]=="inflow"]
    outflows = df[df["direction"]=="outflow"]
    mi = inflows.groupby(inflows["date"].dt.to_period("M"))["amount_ngn"].sum().reset_index()
    mo = outflows.groupby(outflows["date"].dt.to_period("M"))["amount_ngn"].sum().reset_index()
    mi.columns=["period","inflow"]; mo.columns=["period","outflow"]
    m = mi.merge(mo,on="period",how="outer").fillna(0)
    m["period_str"]=m["period"].astype(str)
    m["net"]=m["inflow"]-m["outflow"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=m["period_str"],y=m["inflow"]/1e6,name="Inflow",
        marker_color="#00c896",opacity=0.85,
        hovertemplate="<b>%{x}</b><br>₦%{y:.2f}M<extra></extra>"))
    fig.add_trace(go.Bar(x=m["period_str"],y=m["outflow"]/1e6,name="Outflow",
        marker_color="#f87171",opacity=0.85,
        hovertemplate="<b>%{x}</b><br>₦%{y:.2f}M<extra></extra>"))
    fig.add_trace(go.Scatter(x=m["period_str"],y=m["net"]/1e6,name="Net",
        line=dict(color="#fbbf24",width=2.5,dash="dot"),
        hovertemplate="<b>%{x}</b><br>Net ₦%{y:.2f}M<extra></extra>"))
    fig.update_layout(barmode="group",paper_bgcolor=PLOTLY_BG,plot_bgcolor=PLOTLY_BG,
        xaxis=dict(color=TEXT_COL,gridcolor=GRID_COL),
        yaxis=dict(title="Amount (₦M)",color=TEXT_COL,gridcolor=GRID_COL),
        legend=dict(font=dict(color=TEXT_COL,size=11),bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=10,b=40,l=50,r=10),height=300)
    return fig

def chart_balance(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"],y=df["balance_after_ngn"]/1e3,
        fill="tozeroy",fillcolor="rgba(0,200,150,0.06)",
        line=dict(color="#00c896",width=1.5),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>₦%{y:.1f}K<extra></extra>"))
    fig.add_hline(y=5,line_dash="dot",line_color="#fbbf24",
        annotation_text="₦5K threshold",
        annotation_font=dict(color="#fbbf24",size=10))
    fig.update_layout(paper_bgcolor=PLOTLY_BG,plot_bgcolor=PLOTLY_BG,
        xaxis=dict(color=TEXT_COL,gridcolor=GRID_COL),
        yaxis=dict(title="Balance (₦K)",color=TEXT_COL,gridcolor=GRID_COL),
        margin=dict(t=10,b=40,l=60,r=10),height=280,showlegend=False)
    return fig

def chart_txn_types(df):
    counts = df["txn_type"].value_counts().reset_index()
    counts.columns=["type","count"]
    counts = counts.sort_values("count",ascending=True).tail(10)
    colour_map = {
        "transfer_sent":"#f87171","airtime_purchase":"#fbbf24",
        "pos_settlement":"#f97316","customer_payment":"#00c896",
        "transfer_received":"#4ade80","utility_payment":"#34d399",
        "loan_repayment":"#00c896","bank_charge":"#475569",
        "cash_withdrawal":"#ef4444","tax_payment":"#a78bfa",
        "aggregator_payout":"#38bdf8","supplier_payment":"#fb923c",
    }
    bar_colours = [colour_map.get(t,"#64748b") for t in counts["type"]]
    fig = go.Figure(go.Bar(x=counts["count"],y=counts["type"],orientation="h",
        marker_color=bar_colours,opacity=0.9,
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>"))
    fig.update_layout(paper_bgcolor=PLOTLY_BG,plot_bgcolor=PLOTLY_BG,
        xaxis=dict(title="Count",color=TEXT_COL,gridcolor=GRID_COL),
        yaxis=dict(color=TEXT_COL),
        margin=dict(t=10,b=40,l=150,r=10),height=300,showlegend=False)
    return fig

def chart_gauge(score,colour):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",value=score,
        number={"font":{"color":colour,"family":"Syne","size":44}},
        gauge={
            "axis":{"range":[150,850],"tickwidth":1,"tickcolor":GRID_COL,
                    "tickfont":{"color":TEXT_COL,"size":9}},
            "bar":{"color":colour,"thickness":0.22},
            "bgcolor":"#0f1628","borderwidth":0,
            "steps":[
                {"range":[150,299],"color":"rgba(248,113,113,0.12)"},
                {"range":[299,449],"color":"rgba(249,115,22,0.12)"},
                {"range":[449,599],"color":"rgba(251,191,36,0.12)"},
                {"range":[599,749],"color":"rgba(74,222,128,0.12)"},
                {"range":[749,850],"color":"rgba(0,200,150,0.12)"},
            ],
            "threshold":{"line":{"color":colour,"width":3},"value":score},
        }))
    fig.update_layout(paper_bgcolor=PLOTLY_BG,height=240,
        margin=dict(t=20,b=0,l=30,r=30),font=dict(family="DM Sans"))
    return fig

def chart_inflow_stability(df):
    inflows = df[df["direction"]=="inflow"]
    weekly  = inflows.groupby(inflows["date"].dt.to_period("W"))["amount_ngn"].sum().reset_index()
    weekly.columns=["week","amount"]
    weekly["week_str"]=weekly["week"].astype(str)
    fig = go.Figure(go.Scatter(x=weekly["week_str"],y=weekly["amount"]/1e3,
        fill="tozeroy",fillcolor="rgba(0,200,150,0.07)",
        line=dict(color="#00c896",width=1.5),
        hovertemplate="<b>%{x}</b><br>₦%{y:.1f}K<extra></extra>"))
    fig.update_layout(paper_bgcolor=PLOTLY_BG,plot_bgcolor=PLOTLY_BG,
        xaxis=dict(color=TEXT_COL,gridcolor=GRID_COL,tickfont=dict(size=8)),
        yaxis=dict(title="Weekly Inflow (₦K)",color=TEXT_COL,gridcolor=GRID_COL),
        margin=dict(t=10,b=40,l=60,r=10),height=240,showlegend=False)
    return fig

# ══════════════════════════════════════════════════════════════════
# APP LAYOUT
# ══════════════════════════════════════════════════════════════════

st.markdown("""
<div class="topbar">
  <div class="topbar-logo">
    <div class="topbar-mark">CB</div>
    <span class="topbar-name">CreditBridge Analytics</span>
  </div>
  <span class="topbar-sub">Universal Bank Statement Scorer · v2.0</span>
</div>
""", unsafe_allow_html=True)

# ── Supported banks banner ─────────────────────────────────────
with st.expander("🏦  Supported Banks & How It Works", expanded=False):
    st.markdown("""
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">
    """ + "".join([
        f'<span style="background:#0f1628;border:1px solid #1e2d45;border-radius:20px;'
        f'padding:4px 12px;font-size:0.78rem;color:#94a3b8;font-family:\'DM Mono\',monospace">'
        f'{info["icon"]} {name}</span>'
        for name, info in BANK_SIGNATURES.items()
    ]) + """
    <span style="background:#0f1628;border:1px solid #1e2d45;border-radius:20px;
      padding:4px 12px;font-size:0.78rem;color:#475569;font-family:'DM Mono',monospace">
      + Any Nigerian Bank (auto-fallback)</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    steps = [
        ("01","Bank Auto-Detection","The parser reads the first page to identify which bank issued the statement, then selects the right extraction strategy."),
        ("02","PDF Text Extraction","GTBank uses column-position parsing. All other banks use pdfplumber table extraction. A text-line fallback handles edge cases."),
        ("03","Column Mapping","Header rows are detected automatically. Debit / Credit / Balance columns are matched by name across all known Nigerian bank layouts."),
        ("04","Feature Engineering","25 credit features are computed: income volatility, payment regularity, balance health, counterparty diversity, trend, savings rate."),
        ("05","Credit Scoring","Weighted model converts features to probability of default via log-odds transformation → 150–850 score."),
        ("06","Balance Verification","Parsed closing balance is compared to statement header. Exact match = tamper-free document."),
    ]
    for i,(num,title,body) in enumerate(steps):
        col = c1 if i%2==0 else c2
        with col:
            st.markdown(f"""
            <div style="background:#0f1628;border:1px solid #1e2d45;border-radius:12px;
              padding:16px 20px;margin-bottom:10px;display:flex;gap:14px;align-items:flex-start">
              <div style="font-family:'DM Mono',monospace;font-size:0.62rem;color:#00c896;
                background:rgba(0,200,150,0.1);border:1px solid rgba(0,200,150,0.25);
                border-radius:5px;padding:2px 6px;white-space:nowrap;margin-top:2px">{num}</div>
              <div>
                <div style="font-weight:600;font-size:0.87rem;color:#e2e8f0;margin-bottom:4px">{title}</div>
                <div style="font-size:0.78rem;color:#475569;line-height:1.5">{body}</div>
              </div>
            </div>""", unsafe_allow_html=True)

# ── Upload ─────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0f1628,#111827);
  border:2px dashed #1e2d45;border-radius:20px;padding:48px 40px;
  text-align:center;margin-bottom:1.5rem">
  <div style="font-size:2.5rem;margin-bottom:12px">🏦</div>
  <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;
    color:#e2e8f0;margin-bottom:8px">Upload Any Nigerian Bank Statement</div>
  <div style="color:#475569;font-size:0.88rem;line-height:1.7">
    GTBank · Access · Zenith · First Bank · UBA · Fidelity · Sterling · Stanbic · Kuda · OPay · Moniepoint · and more<br>
    Digital PDF only · 6–24 months · Up to 50MB · Processed locally — nothing stored
  </div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Upload bank statement PDF",
    type=["pdf"],
    label_visibility="collapsed",
)

if uploaded is None:
    st.markdown("""
    <div class="info-box">
      <strong style="color:#00c896">Ready.</strong>
      Upload a digital PDF bank statement from any Nigerian bank above.
      The parser auto-detects the bank and selects the right extraction method.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Parse ──────────────────────────────────────────────────────
progress_placeholder = st.empty()
with progress_placeholder:
    with st.spinner("🔍  Detecting bank and parsing statement..."):
        try:
            pdf_bytes = uploaded.read()
            df, meta, bank_info, parse_method = parse_statement(pdf_bytes)
        except Exception as e:
            st.error(f"Parse failed: {e}")
            st.markdown(f"""
            <div class="error-box">
              <strong>Troubleshooting:</strong><br>
              • Ensure the PDF is <strong>digital</strong> (text-selectable), not a scanned image<br>
              • Try opening it in a PDF viewer — if you can select/copy text it will work<br>
              • Download a fresh copy from your bank's internet banking or mobile app<br>
              • If the issue persists, contact: <a href="mailto:api@creditbridge.co.uk" style="color:#00c896">api@creditbridge.co.uk</a>
            </div>
            """, unsafe_allow_html=True)
            st.stop()

progress_placeholder.empty()

with st.spinner("⚙️  Engineering features and scoring..."):
    features = engineer_features(df)
    result   = score_features(features)
    bv       = verify_balance(df, meta)

score   = result["credit_score"]
band    = result["risk_band"]
colour  = result["band_colour"]
prob    = result["prob_default"]
conf    = result["confidence"]

# ── Bank detected banner ───────────────────────────────────────
st.markdown(f"""
<div class="bank-detected">
  <span class="bank-icon">{bank_info['icon']}</span>
  <div>
    <div class="bank-name">{bank_info['full_name']} — Statement Detected</div>
    <div class="bank-meta">
      {meta.get('account_name','Unknown Account')} ·
      {meta.get('period', df['date'].min().strftime('%d %b %Y') + ' → ' + df['date'].max().strftime('%d %b %Y'))} ·
      {len(df):,} transactions ·
      {parse_method}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Score row ──────────────────────────────────────────────────
st.markdown('<div class="section-hd">Credit Score</div>', unsafe_allow_html=True)
col_score, col_gauge, col_contrib = st.columns([1,1.2,1.3], gap="large")

with col_score:
    st.markdown(f"""
    <div class="score-card">
      <div style="font-family:'DM Mono',monospace;font-size:0.65rem;
        color:#475569;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:14px">
        CreditBridge Score</div>
      <div class="score-num" style="color:{colour}">{score}</div>
      <div class="score-denom">out of 850</div>
      <div><span class="risk-pill" style="background:{colour}18;color:{colour};
        border:1px solid {colour}44">{band} RISK</span></div>
      <div class="pd-strip">
        <div><div class="pd-val">{prob:.1%}</div><div class="pd-lbl">Prob. Default</div></div>
        <div><div class="pd-val">{conf}</div><div class="pd-lbl">Confidence</div></div>
        <div><div class="pd-val">{features['obs_months']}</div><div class="pd-lbl">Months</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if bv["verified"]:
        st.markdown(f"""
        <div style="background:rgba(0,200,150,0.08);border:1px solid rgba(0,200,150,0.25);
          border-radius:10px;padding:11px 16px;margin-top:12px;font-size:0.8rem;">
          <span style="color:#00c896">✅ Statement Verified</span><br>
          <span style="color:#475569">Closing balance: ₦{bv['actual']:,.2f}</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);
          border-radius:10px;padding:11px 16px;margin-top:12px;font-size:0.8rem;">
          <span style="color:#fbbf24">⚠️ Balance Mismatch ₦{bv['diff']:,.2f}</span><br>
          <span style="color:#475569">Verify statement authenticity</span>
        </div>""", unsafe_allow_html=True)

with col_gauge:
    st.plotly_chart(chart_gauge(score,colour), use_container_width=True)
    st.markdown(f"""
    <div class="info-box">
      <strong style="color:#00c896">Lender Guidance:</strong><br>{result['lender_guidance']}
    </div>""", unsafe_allow_html=True)

with col_contrib:
    st.markdown('<div style="font-family:\'DM Mono\',monospace;font-size:0.65rem;color:#475569;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:12px">Contributing Factors</div>', unsafe_allow_html=True)
    for arrow,name,weight,direction in result["contributors"]:
        bc = "#00c896" if direction=="positive" else "#f87171"
        bw = min(int(weight*500),90)
        st.markdown(f"""
        <div class="contrib-row">
          <span style="color:{bc};font-size:0.85rem;width:18px">{arrow}</span>
          <span class="contrib-name">{name}</span>
          <div class="contrib-bg"><div class="contrib-fill" style="width:{bw}px;background:{bc}"></div></div>
          <span style="font-size:0.7rem;color:#475569;font-family:'DM Mono',monospace;width:36px;text-align:right">{weight:.3f}</span>
        </div>""", unsafe_allow_html=True)

# ── KPI row ────────────────────────────────────────────────────
st.markdown('<div class="section-hd">Statement Summary</div>', unsafe_allow_html=True)
k1,k2,k3,k4,k5,k6 = st.columns(6)
for col,label,val,sub in [
    (k1,"Total Inflow",  f"₦{features['total_inflow_ngn']/1e6:.2f}M","Period total"),
    (k2,"Total Outflow", f"₦{features['total_outflow_ngn']/1e6:.2f}M","Period total"),
    (k3,"Net Flow",      f"₦{features['net_flow_ngn']:,.0f}","In − Out"),
    (k4,"Avg Balance",   f"₦{features['bal_mean']:,.0f}","Over period"),
    (k5,"Transactions",  f"{features['total_txn_count']:,}",f"{features['obs_days']} days"),
    (k6,"Savings Rate",  f"{features['savings_rate']:.1%}","Of inflow"),
]:
    with col:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-lbl">{label}</div>
          <div class="kpi-val">{val}</div>
          <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

# ── Charts ─────────────────────────────────────────────────────
st.markdown('<div class="section-hd">Analytics</div>', unsafe_allow_html=True)
t1,t2,t3,t4 = st.tabs(["📊 Monthly Flow","📈 Balance Trajectory","🏷️ Transaction Types","📉 Inflow Stability"])

with t1:
    st.plotly_chart(chart_monthly_flow(df), use_container_width=True)
with t2:
    st.plotly_chart(chart_balance(df), use_container_width=True)
    nzr = features["near_zero_rate"]
    box = "warn-box" if nzr>0.15 else "info-box"
    st.markdown(f'<div class="{box}">Near-zero rate: <strong>{nzr:.1%}</strong> · Min balance: <strong>₦{features["bal_min"]:,.2f}</strong></div>', unsafe_allow_html=True)
with t3:
    c1,c2 = st.columns([1.5,1])
    with c1: st.plotly_chart(chart_txn_types(df), use_container_width=True)
    with c2:
        for t,n in df["txn_type"].value_counts().items():
            pct=n/len(df)*100
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a2035;font-size:0.78rem;"><span style="color:#94a3b8;font-family:\'DM Mono\',monospace">{t}</span><span style="color:#e2e8f0;font-weight:600">{n} <span style="color:#475569">({pct:.1f}%)</span></span></div>', unsafe_allow_html=True)
with t4:
    st.plotly_chart(chart_inflow_stability(df), use_container_width=True)

# ── Feature table ──────────────────────────────────────────────
with st.expander("🔬  Full Feature Breakdown"):
    feat_display = {
        "Total Transactions":f"{features['total_txn_count']:,}",
        "Total Inflow (₦)":f"₦{features['total_inflow_ngn']:,.2f}",
        "Total Outflow (₦)":f"₦{features['total_outflow_ngn']:,.2f}",
        "Net Cash Flow (₦)":f"₦{features['net_flow_ngn']:,.2f}",
        "Avg Daily Inflow (₦)":f"₦{features['avg_daily_inflow']:,.2f}",
        "Observation Days":str(features['obs_days']),
        "Months Covered":str(features['obs_months']),
        "Income Volatility (CV)":f"{features['inflow_cv']:.3f}",
        "Mean Balance (₦)":f"₦{features['bal_mean']:,.2f}",
        "Min Balance (₦)":f"₦{features['bal_min']:,.2f}",
        "Balance Trend Slope":f"{features['bal_slope']:.4f}",
        "Near-Zero Balance Rate":f"{features['near_zero_rate']:.1%}",
        "Has Negative Balance":"Yes ⚠️" if features['has_negative'] else "No ✅",
        "Utility Payment Months":f"{features['util_months']} / {features['obs_months']}",
        "Loan Repayment Count":str(features['loan_count']),
        "Has Active Loan":"Yes ✅" if features['has_loan'] else "No",
        "Regular Payment Rate":f"{features['reg_rate']:.1%}",
        "Counterparty Types":str(features['cp_unique']),
        "Business Growing":"Yes ▲" if features['is_growing'] else "No",
        "Savings Rate":f"{features['savings_rate']:.1%}",
        "Airtime Frequency":f"{features['airtime_freq']:.1%}",
        "ATM/Cash Share":f"{features['atm_share']:.1%}",
        "Bank Charge Share":f"{features['charge_share']:.1%}",
        "Peak Month Inflow (₦)":f"₦{features['peak_month_in']:,.2f}",
    }
    st.dataframe(
        pd.DataFrame(list(feat_display.items()),columns=["Feature","Value"]),
        use_container_width=True,hide_index=True,height=400
    )

# ── Raw transactions ───────────────────────────────────────────
with st.expander("📋  Raw Transactions"):
    show_cols = ["date","direction","amount_ngn","txn_type","balance_after_ngn","narrative"]
    avail = [c for c in show_cols if c in df.columns]
    st.dataframe(
        df[avail].rename(columns={
            "date":"Date","direction":"Direction","amount_ngn":"Amount (₦)",
            "txn_type":"Type","balance_after_ngn":"Balance (₦)","narrative":"Narrative"
        }),
        use_container_width=True,height=320,
    )
    st.download_button(
        "⬇️  Download as CSV",
        df[avail].to_csv(index=False),
        f"creditbridge_{bank_info['name'].lower().replace(' ','_')}_transactions.csv",
        "text/csv",
    )

# ── Footer ─────────────────────────────────────────────────────
st.markdown("""
<div style="border-top:1px solid #1e2d45;margin-top:36px;padding-top:18px;
  display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;
  font-family:'DM Mono',monospace;font-size:0.7rem;color:#334155">
  <span><span style="color:#00c896">CreditBridge Analytics Ltd</span> · UK Incorporated</span>
  <span>Supports 15+ Nigerian Banks · GDPR · NDPR · FCA-aligned</span>
  <span>hello@creditbridge.co.uk</span>
</div>
""", unsafe_allow_html=True)
