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
from src.utils import get_fx_rate, get_realtime_btc_price, clear_data_cache, format_val
from src.config import DEFAULT_NET_WORTH_GOAL, SUPPORTED_CURRENCIES


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
    
    # Apply custom design FIRST
    S.apply_custom_design()
    
    # Sidebar
    with st.sidebar:
        # ===== Logo & Branding =====
        st.markdown("""
        <div style="text-align: center; padding: 8px 0 20px;">
            <div style="font-size: 2.2rem; margin-bottom: 4px;">💰</div>
            <div style="font-size: 1.2rem; font-family: 'Outfit', sans-serif; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">萌の资产中台</div>
            <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 500; margin-top: 2px;">Personal Asset Tracker</div>
        </div>
        """, unsafe_allow_html=True)
        
        # ===== Net Worth Card =====
        try:
            stats = get_sidebar_stats(engine)
            if stats['total_net_worth'] > 0:
                # Get BTC price for conversion
                btc_price = get_realtime_btc_price()
                btc_eq = stats['total_net_worth'] / btc_price if btc_price > 0 else 0
                
                # Goal progress
                goal = st.session_state.get('net_worth_goal', DEFAULT_NET_WORTH_GOAL)
                progress_pct = min(stats['total_net_worth'] / goal * 100, 100) if goal > 0 else 0
                
                currency = st.session_state.get('_currency', 'USD')
                fx_rate_preview, cur_sym_preview = get_fx_rate(currency)
                
                nw_display = "••••••" if st.session_state.get('_privacy', False) else f"{cur_sym_preview}{stats['total_net_worth'] * fx_rate_preview:,.0f}"
                btc_display = "•••• BTC" if st.session_state.get('_privacy', False) else f"≈ {btc_eq:,.4f} BTC"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); padding: 20px; border-radius: 16px; margin-bottom: 20px; position: relative; overflow: hidden;">
                    <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: rgba(16,185,129,0.1); border-radius: 50%;"></div>
                    <div style="position: absolute; bottom: -10px; left: -10px; width: 50px; height: 50px; background: rgba(99,102,241,0.1); border-radius: 50%;"></div>
                    <div style="font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;">总资产净值</div>
                    <div style="font-size: 1.6rem; font-weight: 800; font-family: 'Outfit', sans-serif; color: #FFFFFF; margin: 6px 0 4px; letter-spacing: -0.02em;">{nw_display}</div>
                    <div style="font-size: 0.8rem; color: #F59E0B; font-weight: 600;">🪙 {btc_display}</div>
                    <div style="margin-top: 12px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="font-size: 0.68rem; color: #94A3B8;">🎯 目标进度</span>
                            <span style="font-size: 0.68rem; color: #10B981; font-weight: 700;">{progress_pct:.0f}%</span>
                        </div>
                        <div style="height: 4px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                            <div style="height: 100%; width: {progress_pct}%; background: linear-gradient(90deg, #10B981, #34D399); border-radius: 4px; transition: width 0.6s ease;"></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass
        
        # ===== Navigation =====
        page = st.radio(
            L.SIDEBAR_NAVIGATION,
            [
                f"📊 {L.NAV_DASHBOARD}",
                f"✏️ {L.NAV_ENTRY}",
                f"💰 {L.NAV_PRICES}",
                f"📋 {L.NAV_DATA}"
            ],
            label_visibility="collapsed"
        )
        # Strip emoji prefix for page routing
        page_clean = page.split(" ", 1)[1] if " " in page else page
        
        st.markdown("---")
        
        # ===== Settings Section =====
        with st.expander("⚙️ 设置", expanded=False):
            # Currency selector
            currency = st.selectbox(
                L.SIDEBAR_CURRENCY,
                SUPPORTED_CURRENCIES,
                index=0,
                key="_currency_select"
            )
            st.session_state['_currency'] = currency
            
            # Privacy toggle
            privacy_on = st.toggle(L.SIDEBAR_PRIVACY, value=False, key="_privacy_toggle")
            st.session_state['_privacy'] = privacy_on
            
            # Goal setting  
            goal = st.number_input(
                "🎯 目标净值 (USD)",
                min_value=0,
                value=st.session_state.get('net_worth_goal', DEFAULT_NET_WORTH_GOAL),
                step=10000,
                format="%d"
            )
            st.session_state['net_worth_goal'] = goal
        
        fx_rate, cur_sym = get_fx_rate(currency)
        
        # ===== Quick Actions =====
        if st.button("🔄 刷新数据", use_container_width=True):
            clear_data_cache()
            st.rerun()
        
        # ===== Footer =====
        st.markdown("""
        <div style="position: fixed; bottom: 0; padding: 12px 0; width: 100%;">
            <div style="font-size: 0.65rem; color: #CBD5E1; text-align: center;">
                MyLedger v2.0 · Made with ❤️
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content area - no more redundant title
    # Route to pages
    if page_clean == L.NAV_DASHBOARD:
        show_dashboard(
            engine=engine,
            privacy_on=privacy_on,
            fx_rate=fx_rate,
            cur_sym=cur_sym,
        )

    elif page_clean == L.NAV_ENTRY:
        show_data_entry_page(engine=engine)
    elif page_clean == L.NAV_PRICES:
        show_price_page(engine=engine)
    elif page_clean == L.NAV_DATA:
        show_data_view_page(engine=engine)



# Entry Point
if __name__ == '__main__':
    main()
