import streamlit as st
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timezone
import time

st.set_page_config(page_title="India FII/DII Tracker", page_icon="📊", layout="wide")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "fii_dii_history.csv"
NSE_PAGE = "https://www.nseindia.com/"
NSE_API = "https://www.nseindia.com/api/fiidiiTradeReact"

@st.cache_data(ttl=900, show_spinner=False)
def fetch_nse():
    s = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/reports/fii-dii",
        "Connection": "keep-alive",
    }
    s.headers.update(headers)
    s.get(NSE_PAGE, timeout=20)
    r = s.get(NSE_API, timeout=20)
    r.raise_for_status()
    payload = r.json()
    if isinstance(payload, dict):
        for key in ("data", "dataList", "records"):
            if key in payload and isinstance(payload[key], list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected NSE response: {str(payload)[:300]}")
    df = pd.DataFrame(payload)
    if df.empty:
        raise ValueError("NSE returned an empty response.")
    return df

def first_col(df, candidates):
    lower = {str(c).lower().replace("_", "").replace(" ", ""): c for c in df.columns}
    for name in candidates:
        key = name.lower().replace("_", "").replace(" ", "")
        if key in lower:
            return lower[key]
    return None

def normalize(raw):
    cat = first_col(raw, ["category", "cat"])
    date = first_col(raw, ["date", "tradedate", "timestamp"])
    buy = first_col(raw, ["buyValue", "buy_value", "buy"])
    sell = first_col(raw, ["sellValue", "sell_value", "sell"])
    net = first_col(raw, ["netValue", "net_value", "net"])
    if not all([cat, buy, sell]):
        raise ValueError("Could not identify category/buy/sell columns. NSE may have changed its API schema. Raw columns: " + ", ".join(map(str, raw.columns)))
    out = pd.DataFrame()
    out["category"] = raw[cat].astype(str).str.upper().str.strip()
    out["date"] = raw[date].astype(str) if date else datetime.now().strftime("%d-%b-%Y")
    out["buy_cr"] = pd.to_numeric(raw[buy].astype(str).str.replace(",", ""), errors="coerce")
    out["sell_cr"] = pd.to_numeric(raw[sell].astype(str).str.replace(",", ""), errors="coerce")
    out["net_cr"] = pd.to_numeric(raw[net].astype(str).str.replace(",", ""), errors="coerce") if net else out["buy_cr"] - out["sell_cr"]
    out["source"] = "NSE provisional"
    out = out.dropna(subset=["buy_cr", "sell_cr", "net_cr"])
    return out

def save_history(today):
    if HISTORY_FILE.exists():
        old = pd.read_csv(HISTORY_FILE)
        all_data = pd.concat([old, today], ignore_index=True)
    else:
        all_data = today.copy()
    all_data["date_key"] = pd.to_datetime(all_data["date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
    all_data = all_data.dropna(subset=["date_key"])
    all_data = all_data.drop_duplicates(["date_key", "category"], keep="last")
    all_data = all_data.sort_values(["date_key", "category"])
    all_data.drop(columns=["date_key"]).to_csv(HISTORY_FILE, index=False)
    return all_data.drop(columns=["date_key"])

st.title("🇮🇳 India FII / DII Flow Tracker")
st.caption("Automated daily NSE cash-market flow monitor · Values in ₹ crore · Provisional exchange data")

with st.sidebar:
    st.subheader("Controls")
    refresh = st.button("↻ Refresh NSE data", use_container_width=True)
    st.caption("Automatic refresh cache: 15 minutes")
    st.markdown("[Open official NSE FII/DII report](https://www.nseindia.com/reports/fii-dii)")
    st.markdown("[NSE data notes](https://www.nseindia.com/reports/fii-dii)")

if refresh:
    fetch_nse.clear()

try:
    with st.spinner("Fetching latest NSE FII/DII report..."):
        raw = fetch_nse()
        today = normalize(raw)
        history = save_history(today)
    st.success("NSE data fetched. Latest available report is shown below.")
except Exception as e:
    st.error("Could not retrieve the NSE feed automatically.")
    st.warning("NSE may block automated requests, be temporarily unavailable, or have changed its API response. The dashboard does not fabricate values.")
    st.code(str(e))
    if HISTORY_FILE.exists():
        history = pd.read_csv(HISTORY_FILE)
        st.info("Showing previously collected local history instead.")
    else:
        st.stop()

history["date_parsed"] = pd.to_datetime(history["date"], errors="coerce", dayfirst=True)
history["net_cr"] = pd.to_numeric(history["net_cr"], errors="coerce")
history["buy_cr"] = pd.to_numeric(history["buy_cr"], errors="coerce")
history["sell_cr"] = pd.to_numeric(history["sell_cr"], errors="coerce")
history["category"] = history["category"].astype(str).str.upper()

def get_cat(frame, key):
    x = frame[frame["category"].str.contains(key, na=False)].sort_values("date_parsed")
    return x

fii = get_cat(history, "FII|FPI")
dii = get_cat(history, "DII")

# Latest date available for each group; NSE rows can contain different labels.
fii_latest = fii.iloc[-1] if not fii.empty else None
dii_latest = dii.iloc[-1] if not dii.empty else None

def fmt(v):
    return "—" if pd.isna(v) else f"₹{v:,.0f} Cr"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest FII/FPI net", fmt(fii_latest["net_cr"]) if fii_latest is not None else "—",
          delta="Net buyer" if fii_latest is not None and fii_latest["net_cr"] > 0 else ("Net seller" if fii_latest is not None and fii_latest["net_cr"] < 0 else None))
c2.metric("Latest DII net", fmt(dii_latest["net_cr"]) if dii_latest is not None else "—")
c3.metric("FII 5-session net", fmt(fii.tail(5)["net_cr"].sum()) if not fii.empty else "—")
c4.metric("FII 20-session net", fmt(fii.tail(20)["net_cr"].sum()) if not fii.empty else "—")

if not fii.empty:
    st.subheader("FII/FPI cash-market flow")
    plot = fii.dropna(subset=["date_parsed"]).sort_values("date_parsed").set_index("date_parsed")
    st.bar_chart(plot["net_cr"], height=260)
    roll = plot[["net_cr"]].copy()
    roll["5-session cumulative"] = roll["net_cr"].rolling(5, min_periods=1).sum()
    roll["20-session cumulative"] = roll["net_cr"].rolling(20, min_periods=1).sum()
    st.line_chart(roll[["5-session cumulative", "20-session cumulative"]], height=280)

if not dii.empty:
    st.subheader("DII cash-market flow")
    plot_dii = dii.dropna(subset=["date_parsed"]).sort_values("date_parsed").set_index("date_parsed")
    st.bar_chart(plot_dii["net_cr"], height=200)

st.subheader("Latest NSE rows")
latest_date = history["date_parsed"].max()
latest_rows = history[history["date_parsed"] == latest_date].copy()
st.dataframe(latest_rows[["date", "category", "buy_cr", "sell_cr", "net_cr", "source"]].rename(
    columns={"date":"Date", "category":"Category", "buy_cr":"Buy (₹ Cr)", "sell_cr":"Sell (₹ Cr)", "net_cr":"Net (₹ Cr)", "source":"Source"}),
    use_container_width=True, hide_index=True)

st.subheader("Accumulation / distribution read")
if not fii.empty:
    last5 = fii.tail(5)["net_cr"].sum()
    last20 = fii.tail(20)["net_cr"].sum()
    if last5 > 0 and last20 > 0:
        st.success("FII net accumulation over both the last 5 and 20 available sessions.")
    elif last5 < 0 and last20 < 0:
        st.error("FII net distribution over both the last 5 and 20 available sessions.")
    else:
        st.info("Mixed institutional flow: short- and medium-term FII trends disagree.")
    st.caption("Accumulation is a descriptive flow condition, not a standalone buy signal.")

st.download_button("Download collected history CSV", history.to_csv(index=False).encode("utf-8"),
                   file_name="fii_dii_history.csv", mime="text/csv")
st.caption("Source: NSE FII/FPI & DII trading activity. Data is provisional and may be revised. NSE cash-market activity is not the same as FII index futures/options positioning.")
