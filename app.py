"""
MyLedger - Personal Asset Tracking Tool
Main entry point with modular architecture
"""
import streamlit as st
import pandas as pd
from datetime import date
import os

from src.models import Base, get_engine
from src import lang as L
from src import styles as S

# Import modules
from src.database import (
    save_snapshots_batch, save_transfer,
    get_recent_snapshots, get_recent_transfers,
    get_unique_accounts, get_latest_snapshot_date
)
from src.calculations import (
    calculate_current_net_worth, calculate_transfers_summary,
    calculate_pnl, calculate_time_based_returns,
    get_net_worth_history, get_benchmark_history, get_benchmark_roi
)
from src.auth import check_password
from src import price_service

# Import pages
from pages.dashboard import show_dashboard
from pages.data_entry import show_data_entry_page
from pages.data_view import show_data_view_page
from pages.price import show_price_page
from pages.tips import show_tips_page


# Page config
st.set_page_config(
    page_title=L.APP_TITLE,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Database Configuration
@st.cache_resource
def init_connection():
    db_url = st.secrets.get("DB_URL") or os.getenv("DB_URL") or 'local_ledger.db'
    _engine = get_engine(db_url)
    Base.metadata.create_all(_engine)
    return _engine


engine = init_connection()


# Currency Helper
@st.cache_data(ttl=3600)
def get_fx_rate(to_currency):
    if to_currency == "USD":
        return 1.0, "$"
    
    symbols = {"CNY": "¥", "EUR": "€", "JPY": "¥", "GBP": "£", "HKD": "HK$", "AUD": "A$"}
    symbol = symbols.get(to_currency, to_currency + " ")
    
    service = price_service.PriceService()
    rate = service.fetch_fx_rate(to_currency)
    return rate, symbol


def format_val(val, rate, symbol, privacy_on=False):
    if privacy_on:
        return "••••••"
    return f"{symbol}{val * rate:,.2f}"


# Cache Management
def clear_data_cache():
    """Clear all cached calculations after data changes"""
    st.cache_data.clear()


# Sidebar Stats Cache
@st.cache_data(ttl=60)
def get_sidebar_stats(_engine):
    """Get sidebar stats for display"""
    net_worth = calculate_current_net_worth(_engine)
    return {
        'total_net_worth': net_worth['total_net_worth'],
        'latest_date': get_latest_snapshot_date(_engine)
    }


# Main Application
def main():
    """Main application"""
    # Apply styles
    S.apply_custom_design()

    
    # Check password
    if not check_password():
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"<h1 style='font-size: 1.6rem; margin-bottom: 1.5rem;'>💰 {L.APP_TITLE.split(' - ')[0]}</h1>", unsafe_allow_html=True)
        
        # Currency selector
        currency = st.selectbox(
            L.SIDEBAR_CURRENCY,
            ["USD", "CNY", "EUR", "GBP", "JPY", "HKD", "AUD"],
            index=0
        )
        fx_rate, cur_sym = get_fx_rate(currency)
        
        # Privacy toggle
        privacy_on = st.toggle(L.SIDEBAR_PRIVACY, value=False)
        
        st.markdown("---")
        
        # Goal setting
        goal = st.number_input(
            "🎯 目标净值 (USD)",
            min_value=0,
            value=st.session_state.get('net_worth_goal', 500000),
            step=10000,
            format="%d"
        )
        st.session_state['net_worth_goal'] = goal
        
        # One-click refresh
        if st.button("🔄 刷新数据", use_container_width=True):
            clear_data_cache()
            st.rerun()
        
        st.markdown("---")
        
        # Quick stats
        try:
            stats = get_sidebar_stats(engine)
            if stats['total_net_worth'] > 0:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); padding: 12px; border-radius: 12px; margin-bottom: 8px;'>
                    <div style='font-size: 0.75rem; color: #6B7280;'>当前净值</div>
                    <div style='font-size: 1.3rem; font-weight: 700; font-family: Outfit; color: #10B981;'>
                        {"••••••" if privacy_on else f"{cur_sym}{stats['total_net_worth'] * fx_rate:,.0f}"}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        except:
            pass
        
        st.markdown("---")
        
        # Navigation
        page = st.radio(
            L.SIDEBAR_NAVIGATION,
            [L.NAV_DASHBOARD, L.NAV_ENTRY, L.NAV_PRICES, L.NAV_DATA, L.NAV_TIPS],
            label_visibility="collapsed"
        )
    
    # Main content area
    st.title(L.APP_TITLE)
    
    # Route to pages
    if page == L.NAV_DASHBOARD:
        show_dashboard(
            engine=engine,
            privacy_on=privacy_on,
            fx_rate=fx_rate,
            cur_sym=cur_sym,
            calculate_current_net_worth=calculate_current_net_worth,
            calculate_transfers_summary=calculate_transfers_summary,
            calculate_pnl=calculate_pnl,
            calculate_time_based_returns=calculate_time_based_returns,
            get_benchmark_roi=get_benchmark_roi,
            get_net_worth_history=get_net_worth_history,
            get_benchmark_history=get_benchmark_history,
            format_val=format_val
        )
    elif page == L.NAV_ENTRY:
        show_data_entry_page(
            engine=engine,
            clear_data_cache=clear_data_cache,
            get_unique_accounts=get_unique_accounts,
            calculate_current_net_worth=calculate_current_net_worth,
            save_snapshots_batch=save_snapshots_batch,
            save_transfer=save_transfer
        )
    elif page == L.NAV_PRICES:
        show_price_page(engine=engine, clear_data_cache=clear_data_cache)
    elif page == L.NAV_DATA:
        show_data_view_page(
            engine=engine,
            clear_data_cache=clear_data_cache,
            get_unique_accounts=get_unique_accounts,
            get_recent_snapshots=get_recent_snapshots,
            get_recent_transfers=get_recent_transfers
        )
    elif page == L.NAV_TIPS:
        show_tips_page()


# Entry Point
if __name__ == '__main__':
    main()
