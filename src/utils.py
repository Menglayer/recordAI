"""
Utility functions and helpers
"""
import streamlit as st
from src import price_service


@st.cache_data(ttl=3600)
def get_fx_rate(to_currency):
    """Get exchange rate from USD to target currency"""
    if to_currency == "USD":
        return 1.0, "$"
    
    symbols = {"CNY": "¥", "EUR": "€", "JPY": "¥", "GBP": "£", "HKD": "HK$", "AUD": "A$"}
    symbol = symbols.get(to_currency, to_currency + " ")
    
    service = price_service.PriceService()
    rate = service.fetch_fx_rate(to_currency)
    return rate, symbol


def format_val(val, rate, symbol, privacy_on=False):
    """Format value with currency symbol and privacy mode"""
    if privacy_on:
        return "••••••"
    return f"{symbol}{val * rate:,.2f}"


def clear_data_cache():
    """Clear all cached calculations after data changes"""
    from src.database import (
        get_recent_snapshots, get_recent_transfers, 
        get_unique_accounts, get_latest_snapshot_date, get_price_for_date
    )
    from src.calculations import (
        calculate_current_net_worth, calculate_transfers_summary,
        calculate_pnl, calculate_time_based_returns, 
        get_net_worth_history, calculate_net_worth_for_date, get_benchmark_roi
    )
    
    # Clear database caches
    get_recent_snapshots.clear()
    get_recent_transfers.clear()
    get_unique_accounts.clear()
    get_latest_snapshot_date.clear()
    get_price_for_date.clear()
    
    # Clear calculation caches
    calculate_current_net_worth.clear()
    calculate_transfers_summary.clear()
    calculate_pnl.clear()
    calculate_time_based_returns.clear()
    get_net_worth_history.clear()
    calculate_net_worth_for_date.clear()
    get_benchmark_roi.clear()


# Modern color palette
MODERN_COLORS = [
    '#10B981',  # Emerald
    '#3B82F6',  # Blue
    '#8B5CF6',  # Purple
    '#F59E0B',  # Amber
    '#EF4444',  # Red
    '#06B6D4',  # Cyan
    '#EC4899',  # Pink
    '#6366F1',  # Indigo
]
