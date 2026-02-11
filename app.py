"""
MyLedger - Personal Asset Tracking Tool
Main entry point with modular architecture
"""
import streamlit as st
import os
import pandas as pd
from datetime import datetime

from src.models import Base, get_engine
from src import lang as L
from src import styles as S

from src.calculations import calculate_current_net_worth
from src.database import get_latest_snapshot_date
from src.auth import check_password
from src.utils import get_fx_rate, clear_data_cache

# Import pages
from pages.dashboard import show_dashboard
from pages.data_entry import show_data_entry_page
from pages.data_view import show_data_view_page
from pages.price import show_price_page



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
    # Ensure tables and indexes are created
    Base.metadata.create_all(_engine)
    return _engine





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
    
    # Check password
    if not check_password():
        return
    
    engine = init_connection()
    
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
        
        # Apply custom design
        S.apply_custom_design()
        
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
                # Quick stats card
                card_bg = 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)'
                label_color = '#6B7280'
                
                st.markdown(f"""
                <div style='background: {card_bg}; padding: 12px; border-radius: 12px; margin-bottom: 8px;'>
                    <div style='font-size: 0.75rem; color: {label_color};'>当前净值</div>
                    <div style='font-size: 1.3rem; font-weight: 700; font-family: Outfit; color: #10B981;'>
                        {"••••••" if privacy_on else f"{cur_sym}{stats['total_net_worth'] * fx_rate:,.0f}"}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass
        
        st.markdown("---")
        
        # Navigation
        page = st.radio(
            L.SIDEBAR_NAVIGATION,
            [L.NAV_DASHBOARD, L.NAV_ENTRY, L.NAV_PRICES, L.NAV_DATA],
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
        )

    elif page == L.NAV_ENTRY:
        show_data_entry_page(engine=engine)
    elif page == L.NAV_PRICES:
        show_price_page(engine=engine)
    elif page == L.NAV_DATA:
        show_data_view_page(engine=engine)



# Entry Point
if __name__ == '__main__':
    main()

