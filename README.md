# India FII/DII Automated Tracker

## What this delivers
- Streamlit dashboard that attempts to fetch NSE's public FII/DII cash-market report.
- 15-minute cache and a local CSV history file.
- Latest FII/FPI and DII buy, sell, net values.
- 5-session and 20-session cumulative FII net flows.
- Downloadable collected history.
- Pine Script companion for a future/third-party TradingView feed.

## Important TradingView limitation
Pine Script cannot make arbitrary HTTP requests to NSE. TradingView's Pine Seeds repository creation is currently suspended. The Pine companion is therefore **not automatically connected to NSE**. It requires a data provider that publishes FII/DII flow as TradingView symbols. Do not leave the default NIFTY symbols in place and interpret their prices as FII flow.

## Run on Windows
1. Install Python 3.10 or newer.
2. Extract this folder.
3. Double-click `run_windows.bat`.
4. The browser opens the dashboard.

Or run manually:
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Run on Mac/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Data source and reliability
The app calls the NSE FII/DII report endpoint used by the public report page. NSE may change or restrict this endpoint, and automated access may fail from some networks. The app shows an error rather than inventing values. NSE figures are provisional and may be revised. The local history starts accumulating only after you run the app; it does not backfill a full historical series.

Official report: https://www.nseindia.com/reports/fii-dii

## Operational notes
- Keep the app running to refresh and collect each day's data.
- The 15-minute cache reduces repeated requests. Use Refresh NSE data to force a refresh.
- For dependable unattended collection, deploy on an always-on machine/server and schedule a daily fetch. NSE anti-bot controls can still interrupt collection.
- This version covers cash-market FII/FPI and DII activity only. It does not infer FII index futures/options positions from cash data.
