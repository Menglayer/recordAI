# MyLedger - Personal Asset Tracker

Personal asset tracking tool with dashboard analytics, price fetching, and APY calculation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python tools/db_init.py

# Run app
streamlit run app.py
```

## Project Structure

```
recordAI/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── local_ledger.db     # SQLite database
├── src/                # Core modules
│   ├── models.py       # Database models
│   └── price_service.py # Price fetching service
├── tools/              # CLI tools
│   ├── update_prices.py   # Update asset prices
│   ├── diagnose.py        # Data diagnostic
│   ├── reset_database.py  # Reset database
│   └── db_init.py         # Initialize database
└── docs/               # Documentation
    ├── APY_CALCULATION_GUIDE.md
    ├── DASHBOARD_GUIDE.md
    ├── DATA_ENTRY_GUIDE.md
    ├── PRICE_SERVICE_DOCS.md
    ├── PROJECT_SUMMARY.md
    └── QUICK_START.md
```

## Features

- **Dashboard**: Net worth, PnL, ROI, APY, charts
- **Data Entry**: Snapshots "and transfers
- **Price Update**: Auto-fetch from CCXT/yfinance
- **Data View**: View all records

## CLI Tools

Run from project root:

```bash
# Update prices from snapshots
cd tools && python update_prices.py

# Diagnose data issues
cd tools && python diagnose.py

# Reset database
cd tools && python reset_database.py
```

## Tech Stack

- Streamlit (UI)
- SQLAlchemy (ORM)
- SQLite (Database)
- Plotly (Charts)
- CCXT/yfinance (Prices)
