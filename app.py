"""
MyLedger - Personal Asset Tracking Tool
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from src.models import Base, get_engine, get_session, Snapshot, Transfer, PriceHistory
from sqlalchemy import and_
import os
from src import price_service
from src import lang as L
from src import styles as S

# Page config
st.set_page_config(
    page_title=L.APP_TITLE,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database Configuration - Cached for Speed
@st.cache_resource
def init_connection():
    # Priority: Streamlit Secrets -> Environment Variable -> Local SQLite
    db_url = st.secrets.get("DB_URL") or os.getenv("DB_URL") or 'local_ledger.db'
    _engine = get_engine(db_url)
    
    # Only create tables once per server session
    Base.metadata.create_all(_engine)
    return _engine

engine = init_connection()

# ============ Currency Helper ============
@st.cache_data(ttl=3600)  # Cache FX rates for 1 hour
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

# ============ Cache Management ============

def clear_data_cache():
    """Clear all cached calculations after data changes"""
    # Clear all st.cache_data functions
    st.cache_data.clear()
    
    # Also explicitly clear cached functions (belt and suspenders)
    for func in [
        calculate_net_worth_for_date,
        calculate_current_net_worth,
        get_net_worth_history,
        calculate_transfers_summary,
        calculate_pnl,
        calculate_time_based_returns,
        get_sidebar_stats,
        get_benchmark_roi
    ]:
        try:
            func.clear()
        except:
            pass

# ============ Database Functions ============

def save_snapshots_batch(snapshot_date, account_name, snapshot_data):
    """Save batch snapshots"""
    session = get_session(engine)
    saved_count = 0
    
    try:
        for _, row in snapshot_data.iterrows():
            symbol = str(row['Symbol']).strip().upper()
            quantity = float(row['Quantity'])
            
            if not symbol or symbol == '' or quantity < 0:
                continue
            
            existing = session.query(Snapshot).filter(
                and_(
                    Snapshot.date == snapshot_date,
                    Snapshot.account_name == account_name,
                    Snapshot.symbol == symbol
                )
            ).first()
            
            if existing:
                existing.quantity = quantity
                existing.created_at = datetime.utcnow()
            else:
                new_snapshot = Snapshot(
                    date=snapshot_date,
                    account_name=account_name,
                    symbol=symbol,
                    quantity=quantity
                )
                session.add(new_snapshot)
            
            saved_count += 1
        
        session.commit()
        clear_data_cache()  # Invalidate cache after saving
        return saved_count
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_transfer(transfer_date, transfer_type, amount_usd, note=None):
    """Save transfer record"""
    session = get_session(engine)
    
    try:
        new_transfer = Transfer(
            date=transfer_date,
            type=transfer_type,
            amount_usd=amount_usd,
            note=note
        )
        session.add(new_transfer)
        session.commit()
        clear_data_cache()  # Invalidate cache after saving
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_recent_snapshots(limit=10):
    """Get recent snapshots"""
    session = get_session(engine)
    try:
        snapshots = session.query(Snapshot).order_by(
            Snapshot.date.desc(), Snapshot.created_at.desc()
        ).limit(limit).all()
        return snapshots
    finally:
        session.close()


def get_recent_transfers(limit=10):
    """Get recent transfers"""
    session = get_session(engine)
    try:
        transfers = session.query(Transfer).order_by(
            Transfer.date.desc(), Transfer.created_at.desc()
        ).limit(limit).all()
        return transfers
    finally:
        session.close()


def get_unique_accounts():
    """Get unique account names"""
    session = get_session(engine)
    try:
        accounts = session.query(Snapshot.account_name).distinct().all()
        return [a[0] for a in accounts if a[0]]
    finally:
        session.close()


# ============ Calculation Functions ============

@st.cache_data(ttl=300)
def get_latest_snapshot_date():
    """Get latest snapshot date"""
    session = get_session(engine)
    try:
        latest = session.query(Snapshot.date).order_by(Snapshot.date.desc()).first()
        return latest[0] if latest else None
    finally:
        session.close()


@st.cache_data(ttl=600)
def get_price_for_date(symbol, target_date):
    """Get price for date, use latest if not available"""
    session = get_session(engine)
    try:
        price_record = session.query(PriceHistory).filter(
            and_(
                PriceHistory.symbol == symbol,
                PriceHistory.date == target_date
            )
        ).first()
        
        if price_record:
            return price_record.price_usd
        
        price_record = session.query(PriceHistory).filter(
            and_(
                PriceHistory.symbol == symbol,
                PriceHistory.date <= target_date
            )
        ).order_by(PriceHistory.date.desc()).first()
        
        return price_record.price_usd if price_record else None
        
    finally:
        session.close()


@st.cache_data(ttl=600)
def calculate_net_worth_for_date(target_date):
    """Calculate net worth for date"""
    session = get_session(engine)
    try:
        snapshots = session.query(Snapshot).filter(Snapshot.date == target_date).all()
        
        if not snapshots:
            return pd.DataFrame()
        
        data = []
        for s in snapshots:
            price = get_price_for_date(s.symbol, target_date)
            value = s.quantity * price if price else 0
            data.append({
                'account_name': s.account_name,
                'symbol': s.symbol,
                'quantity': s.quantity,
                'price': price or 0,
                'value': value
            })
        
        return pd.DataFrame(data)
        
    finally:
        session.close()


@st.cache_data(ttl=600)
def calculate_current_net_worth():
    """Calculate current net worth"""
    latest_date = get_latest_snapshot_date()
    
    if not latest_date:
        return {
            'latest_date': None,
            'total_net_worth': 0,
            'details': pd.DataFrame(),
            'by_symbol': pd.DataFrame(),
            'by_account': pd.DataFrame()
        }
    
    details_df = calculate_net_worth_for_date(latest_date)
    
    if details_df.empty:
        return {
            'latest_date': latest_date,
            'total_net_worth': 0,
            'details': pd.DataFrame(),
            'by_symbol': pd.DataFrame(),
            'by_account': pd.DataFrame()
        }
    
    total_net_worth = details_df['value'].sum()
    
    by_symbol = details_df.groupby('symbol').agg({
        'quantity': 'sum',
        'value': 'sum'
    }).reset_index()
    
    by_account = details_df.groupby('account_name').agg({
        'value': 'sum'
    }).reset_index()
    
    return {
        'latest_date': latest_date,
        'total_net_worth': total_net_worth,
        'details': details_df,
        'by_symbol': by_symbol,
        'by_account': by_account
    }


@st.cache_data(ttl=300)
def calculate_transfers_summary():
    """Calculate transfers summary"""
    session = get_session(engine)
    
    try:
        transfers = session.query(Transfer).all()
        
        total_deposits = sum(t.amount_usd for t in transfers if t.type == 'deposit')
        total_withdrawals = sum(t.amount_usd for t in transfers if t.type == 'withdrawal')
        
        return {
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'net_investment': total_deposits - total_withdrawals
        }
        
    finally:
        session.close()


@st.cache_data(ttl=300)
def calculate_pnl():
    """Calculate PnL"""
    net_worth_data = calculate_current_net_worth()
    transfers_data = calculate_transfers_summary()
    
    current_net_worth = net_worth_data['total_net_worth']
    net_investment = transfers_data['net_investment']
    
    if net_investment == 0:
        unrealized_pnl = current_net_worth
        roi_percentage = 0
    else:
        unrealized_pnl = current_net_worth - net_investment
        roi_percentage = (unrealized_pnl / net_investment) * 100 if net_investment > 0 else 0
    
    return {
        'unrealized_pnl': unrealized_pnl,
        'roi_percentage': roi_percentage,
        'current_net_worth': current_net_worth,
        'net_investment': net_investment
    }


@st.cache_data(ttl=300)
def calculate_time_based_returns():
    """Calculate time-based returns and APY"""
    session = get_session(engine)
    
    try:
        snapshots = session.query(Snapshot.date, Snapshot.created_at).order_by(
            Snapshot.date, Snapshot.created_at
        ).all()
        
        if len(snapshots) < 2:
            return {'has_data': False, 'roi': 0, 'apy': 0, 'days': 0, 'hours': 0}
        
        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]
        
        start_date = first_snapshot[0]
        end_date = last_snapshot[0]
        
        start_datetime = datetime.combine(first_snapshot[0], datetime.min.time())
        end_datetime = datetime.combine(last_snapshot[0], datetime.min.time())
        
        if first_snapshot[1] and last_snapshot[1]:
            if isinstance(first_snapshot[1], datetime):
                start_datetime = first_snapshot[1]
            if isinstance(last_snapshot[1], datetime):
                end_datetime = last_snapshot[1]
        
        time_delta = end_datetime - start_datetime
        total_hours = time_delta.total_seconds() / 3600
        total_days = time_delta.total_seconds() / 86400
        
        if total_hours < 1:
            return {'has_data': False, 'roi': 0, 'apy': 0, 'days': 0, 'hours': 0}
        
        start_net_worth_df = calculate_net_worth_for_date(start_date)
        end_net_worth_df = calculate_net_worth_for_date(end_date)
        
        start_net_worth = start_net_worth_df['value'].sum() if not start_net_worth_df.empty else 0
        end_net_worth = end_net_worth_df['value'].sum() if not end_net_worth_df.empty else 0
        
        transfers = session.query(Transfer).filter(
            and_(Transfer.date > start_date, Transfer.date <= end_date)
        ).all()
        
        period_deposits = sum(t.amount_usd for t in transfers if t.type == 'deposit')
        period_withdrawals = sum(t.amount_usd for t in transfers if t.type == 'withdrawal')
        net_cash_flow = period_deposits - period_withdrawals
        
        if start_net_worth > 0:
            roi = ((end_net_worth - start_net_worth - net_cash_flow) / start_net_worth) * 100
        else:
            roi = 0
        
        hours_per_year = 365.25 * 24
        
        # APR: Simple annualized return (linear extrapolation)
        if total_days > 0:
            apr = (roi / total_days) * 365.25
        else:
            apr = 0
        
        # APY: Compound annualized return (CAGR)
        if total_hours > 0 and roi > -100:
            apy = (((1 + roi/100) ** (hours_per_year / total_hours)) - 1) * 100
        else:
            apy = 0
        
        return {
            'has_data': True,
            'roi': roi,
            'apr': apr,  # Simple annualized
            'apy': apy,  # Compound annualized
            'days': total_days,
            'hours': total_hours,
            'start_date': start_date,
            'end_date': end_date,
            'start_net_worth': start_net_worth,
            'end_net_worth': end_net_worth,
            'net_cash_flow': net_cash_flow,
            'period_deposits': period_deposits,
            'period_withdrawals': period_withdrawals
        }
        
    finally:
        session.close()


@st.cache_data(ttl=600)
def get_net_worth_history():
    """Get net worth history"""
    session = get_session(engine)
    
    try:
        dates = session.query(Snapshot.date).distinct().order_by(Snapshot.date).all()
        dates = [d[0] for d in dates]
        
        if not dates:
            return pd.DataFrame()
        
        history = []
        for d in dates:
            net_worth_df = calculate_net_worth_for_date(d)
            total = net_worth_df['value'].sum() if not net_worth_df.empty else 0
            history.append({'date': d, 'net_worth': total})
        
        return pd.DataFrame(history)
        
    finally:
        session.close()


@st.cache_data(ttl=3600)
def get_benchmark_history(start_date, end_date):
    """Fetch benchmark price history using yfinance"""
    import yfinance as yf
    from datetime import datetime, timedelta, date
    
    benchmarks = {
        'S&P500': '^GSPC',
        'QQQ': 'QQQ',
        'BTC': 'BTC-USD',
        '沪深300': '000300.SS'
    }
    
    result = {}
    
    # Convert dates to string format for yfinance
    if isinstance(start_date, date):
        start_str = start_date.strftime('%Y-%m-%d')
    else:
        start_str = str(start_date)
    
    if isinstance(end_date, date):
        end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        end_str = str(end_date)
    
    for name, ticker in benchmarks.items():
        try:
            data = yf.download(
                ticker, 
                start=start_str, 
                end=end_str,
                progress=False,
                auto_adjust=True
            )
            
            if not data.empty:
                # Handle multi-level columns (yfinance sometimes returns this)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                # Get closing prices
                prices = data[['Close']].reset_index()
                prices.columns = ['date', 'price']
                
                # Convert date to date object for consistency
                prices['date'] = pd.to_datetime(prices['date']).dt.date
                prices['price'] = pd.to_numeric(prices['price'], errors='coerce')
                prices = prices.dropna()
                
                if len(prices) > 0:
                    result[name] = prices
        except Exception as e:
            # Silently skip failed benchmarks
            pass
    
    return result


# ============ Authentication ============

def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("PASSWORD", "admin123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Professional Login Screen - Unified
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
            
            # Start the Card Wrapper
            st.markdown(f"""
                <div class="u-card" style='text-align: center; padding: 40px; margin-bottom: 0px;'>
                    <div style='background: #F8FAFC; width: 64px; height: 64px; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto;'>
                        <span style='font-size: 32px;'>🔐</span>
                    </div>
                    <h2 style='margin-bottom: 8px; font-size: 1.8rem;'>{L.APP_TITLE.split(" - ")[0]}</h2>
                    <p style='color: var(--falcon-muted); margin-bottom: 32px; font-size: 0.95rem;'>请验证访问授权</p>
                </div>
            """, unsafe_allow_html=True)
            
            # The input follows immediately without gap
            st.text_input(
                "Access Key", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="键入密码并回车",
                label_visibility="collapsed"
            )
            
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.markdown("""
                    <div style='background-color: #FEF2F2; color: #DC2626; padding: 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; text-align: center; margin-top: 15px; border: 1px solid #FEE2E2;'>
                        ❌ 密码错误，请核对后重试
                    </div>
                """, unsafe_allow_html=True)
            
        return False
    else:
        return st.session_state["password_correct"]

# ============ Global Cache Helpers ============

@st.cache_data(ttl=600)
def get_sidebar_stats(engine_trigger): # Trigger is just to ensure it's tied to engine state if needed
    session = get_session(engine)
    try:
        snapshot_count = session.query(Snapshot).count()
        transfer_count = session.query(Transfer).count()
        price_count = session.query(PriceHistory).count()
        return snapshot_count, transfer_count, price_count
    finally:
        session.close()

@st.cache_data(ttl=600)
def get_benchmark_roi(engine_trigger):
    """Quick Benchmark (BTC ROI since first snapshot)"""
    try:
        session = get_session(engine)
        first_snapshot = session.query(Snapshot.date).order_by(Snapshot.date.asc()).first()
        if first_snapshot:
            # Get latest BTC and BTC at first snapshot date
            btc_current = session.query(PriceHistory.price_usd).filter(PriceHistory.symbol=='BTC').order_by(PriceHistory.date.desc()).first()
            btc_start = session.query(PriceHistory.price_usd).filter(PriceHistory.symbol=='BTC', PriceHistory.date <= first_snapshot[0]).order_by(PriceHistory.date.desc()).first()
            if btc_current and btc_start and btc_start[0] > 0:
                roi = ((btc_current[0] / btc_start[0]) - 1) * 100
                session.close()
                return roi
        session.close()
    except:
        pass
    return 0.0

# ============ Main Application ============

def main():
    """Main application"""
    # Apply modern design
    S.apply_custom_design()
    
    if not check_password():
        st.stop()  # Do not run the rest of the app
    
    # --- Sidebar Configuration & Tools ---
    with st.sidebar:
        st.markdown(f'<div style="padding: 10px 16px 20px 16px;"><h2 style="font-size:1.1rem; margin:0;">Account</h2></div>', unsafe_allow_html=True)
        
        # Privacy & Currency
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            privacy_on = st.toggle("🔒 隐私", value=st.session_state.get('privacy_mode', False))
            st.session_state['privacy_mode'] = privacy_on
        with col_s2:
            currency = st.selectbox("Currency", ["USD", "CNY", "EUR", "JPY", "HKD", "GBP"], index=0, label_visibility="collapsed")
        
        fx_rate, cur_sym = get_fx_rate(currency)
        
        # Show exchange rate
        if currency != "USD":
            st.caption(f"💱 1 USD = {fx_rate:.4f} {currency}")
        
        # One-click refresh button
        if st.button("🔄 刷新数据", use_container_width=True):
            clear_data_cache()
            st.toast("✅ 缓存已清除，数据已刷新", icon="🔄")
            st.rerun()
        
        # Side Navigation
        page = st.radio(
            "Menu", # This will be hidden by CSS
            [L.NAV_DASHBOARD, L.NAV_DATA_ENTRY, L.NAV_PRICE_UPDATE, L.NAV_DATA_VIEW],
            index=0
        )
        
        st.markdown("---")
        
        # Goal Tracking
        st.markdown("##### 🎯 目标追踪")
        
        # Initialize goal in session state
        if 'net_worth_goal' not in st.session_state:
            st.session_state['net_worth_goal'] = 500000
        
        goal = st.number_input(
            "目标净值 (USD)",
            min_value=1000,
            max_value=100000000,
            value=st.session_state['net_worth_goal'],
            step=10000,
            label_visibility="collapsed"
        )
        st.session_state['net_worth_goal'] = goal
        
        st.markdown("<div style='flex-grow:1; height: 30px;'></div>", unsafe_allow_html=True)
        
        # Bottom Stats Card
        st.markdown('<div class="side-stats">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:0.65rem; font-weight:700; color:#9CA3AF; text-transform:uppercase; margin-bottom:12px;">{L.SIDEBAR_STATS}</div>', unsafe_allow_html=True)
        
        counts = get_sidebar_stats(str(engine.url))
        for lab, val in [(L.STAT_SNAPSHOTS, counts[0]), (L.STAT_TRANSFERS, counts[1]), (L.STAT_PRICES, counts[2])]:
            st.markdown(f'<div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span style="color:#6B7280; font-size:0.75rem;">{lab}</span><span style="font-weight:700; font-size:0.75rem;">{val}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Page Routing
    if page == L.NAV_DASHBOARD:
        show_dashboard(privacy_on, fx_rate, cur_sym)
    elif page == L.NAV_DATA_ENTRY:
        show_data_entry_page()
    elif page == L.NAV_PRICE_UPDATE:
        show_price_page()
    elif page == L.NAV_DATA_VIEW:
        show_data_view_page()


def show_dashboard(privacy_on=False, fx_rate=1.0, cur_sym="$"):
    """Dashboard page with Benchmarking"""
    st.markdown("---")
    
    # Loading spinner while calculating data
    with st.spinner("📊 正在加载数据..."):
        net_worth_data = calculate_current_net_worth()
        transfers_data = calculate_transfers_summary()
        pnl_data = calculate_pnl()
        time_returns = calculate_time_based_returns()
        benchmark_roi = get_benchmark_roi(str(engine.url))
    
    # Filter out archived accounts from current display
    archived = st.session_state.get('archived_accounts', [])
    if not net_worth_data['details'].empty:
        filtered_details = net_worth_data['details'].copy()
        
        # Filter out archived accounts
        if archived:
            filtered_details = filtered_details[~filtered_details['account_name'].isin(archived)]
        
        # Filter out accounts with value < $10 for display (but keep in total)
        total_net_worth = filtered_details['value'].sum() if not filtered_details.empty else 0
        display_details = filtered_details[filtered_details['value'] >= 10]
        
        # Recalculate display data (excluding small accounts from charts)
        net_worth_data = {
            'latest_date': net_worth_data['latest_date'],
            'total_net_worth': total_net_worth,  # Total includes all accounts
            'details': display_details,  # Display excludes < $10
            'by_symbol': display_details.groupby('symbol').agg({'quantity': 'sum', 'value': 'sum'}).reset_index() if not display_details.empty else pd.DataFrame(),
            'by_account': display_details.groupby('account_name').agg({'value': 'sum'}).reset_index() if not display_details.empty else pd.DataFrame()
        }

    # Data date - Enhanced Typography
    st.markdown(f"""
        <div style='margin: 0 0 2rem 0; display: flex; align-items: baseline; gap: 15px;'>
            <h2 style='margin: 0; font-size: 1.7rem;'>{L.DASH_DATA_DATE} <span style='font-family: Outfit; font-weight: 700;'>{net_worth_data['latest_date']}</span></h2>
            <span style='color: var(--falcon-muted); font-size: 0.85rem; font-weight: 500;'>{L.DASH_BASED_ON}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Net Worth prominently
    S.metric_card(
        label=L.DASH_NET_WORTH,
        value=format_val(net_worth_data['total_net_worth'], fx_rate, cur_sym),
        is_masked=privacy_on
    )
    
    # Goal Progress Bar - Premium Design
    goal = st.session_state.get('net_worth_goal', 500000)
    current_nw = net_worth_data['total_net_worth']
    progress = min(current_nw / goal, 1.0) if goal > 0 else 0
    progress_pct = progress * 100
    remaining = max(0, goal - current_nw)
    
    # Determine status and colors
    if progress >= 1:
        status_icon = "🎉"
        status_text = "恭喜！目标达成！"
        gradient = "linear-gradient(90deg, #10B981, #34D399, #6EE7B7)"
        glow_color = "rgba(16, 185, 129, 0.4)"
    elif progress >= 0.75:
        status_icon = "🔥"
        status_text = f"冲刺中！还差 {cur_sym}{remaining * fx_rate:,.0f}"
        gradient = "linear-gradient(90deg, #0EA5E9, #38BDF8, #7DD3FC)"
        glow_color = "rgba(14, 165, 233, 0.4)"
    elif progress >= 0.5:
        status_icon = "📈"
        status_text = f"进展顺利！还差 {cur_sym}{remaining * fx_rate:,.0f}"
        gradient = "linear-gradient(90deg, #6366F1, #818CF8, #A5B4FC)"
        glow_color = "rgba(99, 102, 241, 0.4)"
    else:
        status_icon = "🎯"
        status_text = f"努力中！还差 {cur_sym}{remaining * fx_rate:,.0f}"
        gradient = "linear-gradient(90deg, #F59E0B, #FBBF24, #FDE047)"
        glow_color = "rgba(245, 158, 11, 0.4)"
    
    if not privacy_on:
        st.markdown(f"""
            <div class="u-card" style="padding: 1.5rem; margin: 0.5rem 0 2rem 0; position: relative; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 2rem; animation: bounce 1s infinite;">{status_icon}</span>
                        <div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #1F2937;">目标进度</div>
                            <div style="font-size: 0.8rem; color: #6B7280; margin-top: 2px;">{status_text}</div>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 2.5rem; font-weight: 800; font-family: Outfit; background: {gradient}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: pulse 2s infinite;">{progress_pct:.1f}%</div>
                    </div>
                </div>
                <div style="background: #E5E7EB; border-radius: 16px; height: 28px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1); position: relative;">
                    <div class="progress-fill" style="background: {gradient}; width: {progress_pct}%; height: 100%; border-radius: 16px; position: relative; box-shadow: 0 0 20px {glow_color}, 0 0 40px {glow_color}; animation: glow 2s ease-in-out infinite;">
                        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.5) 50%, transparent 100%); animation: shine 2s ease-in-out infinite;"></div>
                        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 0.75rem; font-weight: 700; color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.3);"></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 14px; font-size: 0.85rem;">
                    <div style="text-align: left;">
                        <div style="color: #9CA3AF; font-size: 0.7rem; text-transform: uppercase;">当前</div>
                        <div style="font-weight: 700; color: #374151; font-family: Outfit;">{cur_sym}{current_nw * fx_rate:,.0f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: #9CA3AF; font-size: 0.7rem; text-transform: uppercase;">进度</div>
                        <div style="font-weight: 700; color: #374151;">{progress_pct:.1f}%</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #9CA3AF; font-size: 0.7rem; text-transform: uppercase;">目标</div>
                        <div style="font-weight: 700; color: #374151; font-family: Outfit;">{cur_sym}{goal * fx_rate:,.0f}</div>
                    </div>
                </div>
            </div>
            <style>
                @keyframes shine {{
                    0% {{ transform: translateX(-100%); }}
                    50% {{ transform: translateX(100%); }}
                    100% {{ transform: translateX(100%); }}
                }}
                @keyframes glow {{
                    0%, 100% {{ box-shadow: 0 0 15px {glow_color}, 0 0 30px {glow_color}; }}
                    50% {{ box-shadow: 0 0 25px {glow_color}, 0 0 50px {glow_color}; }}
                }}
                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.8; }}
                }}
                @keyframes bounce {{
                    0%, 100% {{ transform: translateY(0); }}
                    50% {{ transform: translateY(-5px); }}
                }}
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="u-card" style="padding: 1.5rem; margin: 0.5rem 0 2rem 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 2rem;">🎯</span>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #1F2937;">目标进度</div>
                    </div>
                    <span style="font-size: 1.5rem; font-weight: 600;">••••••</span>
                </div>
                <div style="background: #E5E7EB; border-radius: 16px; height: 28px;"></div>
            </div>
        """, unsafe_allow_html=True)
    
    # Other metrics in one row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        S.metric_card(
            label=L.DASH_INVESTED,
            value=format_val(transfers_data['net_investment'], fx_rate, cur_sym),
            delta=f"{format_val(transfers_data['total_deposits'], fx_rate, cur_sym)} 入 | {format_val(transfers_data['total_withdrawals'], fx_rate, cur_sym)} 出",
            delta_up="neutral",
            is_masked=privacy_on
        )
    
    with col2:
        pnl_value = pnl_data['unrealized_pnl']
        S.metric_card(
            label=L.DASH_PNL,
            value=format_val(pnl_value, fx_rate, cur_sym),
            delta=f"{pnl_data['roi_percentage']:.2f}%",
            delta_up=pnl_value >= 0,
            is_masked=privacy_on,
            benchmark=f"BTC {benchmark_roi:+.1f}%" if benchmark_roi != 0 else None
        )
    
    with col3:
        roi_pct = pnl_data['roi_percentage']
        S.metric_card(
            label=L.DASH_ROI,
            value=f"{roi_pct:.2f}%",
            delta=L.DASH_PROFIT if roi_pct > 0 else L.DASH_LOSS if roi_pct < 0 else L.DASH_EVEN,
            delta_up=roi_pct >= 0
        )
    
    # Time-based returns
    if time_returns['has_data']:
        st.markdown("---")
        st.subheader(L.TIME_RETURNS)
        
        # Privacy helper
        def mask(val):
            return "••••••" if privacy_on else val
        
        col_time1, col_time2, col_time3 = st.columns(3)
        
        with col_time1:
            st.markdown(f"""
            <div class="u-card" style="padding: 20px;">
                <div class="m-label">{L.TIME_PERIOD}</div>
                <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                    <div><span style="color: var(--falcon-muted);">{L.TIME_START}:</span> <strong>{time_returns['start_date']}</strong></div>
                    <div><span style="color: var(--falcon-muted);">{L.TIME_END}:</span> <strong>{time_returns['end_date']}</strong></div>
                    <div><span style="color: var(--falcon-muted);">{L.TIME_DAYS}:</span> <strong>{time_returns['days']:.1f}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_time2:
            start_val = mask(format_val(time_returns['start_net_worth'], fx_rate, cur_sym))
            end_val = mask(format_val(time_returns['end_net_worth'], fx_rate, cur_sym))
            change_val = mask(format_val(time_returns['end_net_worth'] - time_returns['start_net_worth'], fx_rate, cur_sym))
            
            st.markdown(f"""
            <div class="u-card" style="padding: 20px;">
                <div class="m-label">{L.TIME_NW_CHANGE}</div>
                <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                    <div><span style="color: var(--falcon-muted);">{L.TIME_START}:</span> <strong>{start_val}</strong></div>
                    <div><span style="color: var(--falcon-muted);">{L.TIME_END}:</span> <strong>{end_val}</strong></div>
                    <div><span style="color: var(--falcon-muted);">{L.TIME_CHANGE}:</span> <strong>{change_val}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_time3:
            deposits = mask(f"{cur_sym}{time_returns.get('period_deposits', 0) * fx_rate:,.2f}")
            withdrawals = mask(f"{cur_sym}{time_returns.get('period_withdrawals', 0) * fx_rate:,.2f}")
            net_flow = mask(f"{cur_sym}{time_returns['net_cash_flow'] * fx_rate:,.2f}")
            
            st.markdown(f"""
            <div class="u-card" style="padding: 20px;">
                <div class="m-label">{L.TIME_CASH_FLOW}</div>
                <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                    <div><span style="color: var(--falcon-muted);">{L.TIME_DEPOSITS}:</span> <strong style="color: #10B981;">{deposits}</strong></div>
                    <div><span style="color: var(--falcon-muted);">{L.TIME_WITHDRAWALS}:</span> <strong style="color: #EF4444;">{withdrawals}</strong></div>
                    <div><span style="color: var(--falcon-muted);">{L.TIME_NET}:</span> <strong>{net_flow}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        col_apy1, col_apy2, col_apy3 = st.columns(3)
        
        with col_apy1:
            roi_val = f"{time_returns['roi']:.2f}%"
            S.metric_card(
                label=L.TIME_PERIOD_ROI,
                value=roi_val,
                delta=f"{time_returns['days']:.1f} 天",
                delta_up=time_returns['roi'] >= 0
            )
        
        with col_apy2:
            apr_val = f"{time_returns['apr']:,.2f}%"
            S.metric_card(
                label="年化收益 (APR)",
                value=apr_val,
                delta="简单年化",
                delta_up=time_returns['apr'] >= 0
            )
        
        with col_apy3:
            apy_val = f"{time_returns['apy']:,.2f}%"
            S.metric_card(
                label="复利年化 (APY)",
                value=apy_val,
                delta="复利计算" if abs(time_returns['apy']) < 1000 else L.TIME_HIGH_VOL,
                delta_up=time_returns['apy'] >= 0
            )
    
    st.markdown("---")
    
    # Time Period Filter
    st.markdown("##### 📈 数据可视化")
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    with filter_col1:
        time_filter = st.segmented_control(
            "时间筛选",
            options=["7D", "30D", "90D", "全部"],
            default="全部",
            label_visibility="collapsed"
        )
    
    # Charts
    if net_worth_data['details'].empty or net_worth_data['details']['price'].sum() == 0:
        st.warning(L.CHART_MISSING_PRICE)
    
    # Falcon Finance Colors: Emerald (USDT style), Orange, Blue, Indigo, Amber
    MODERN_COLORS = ['#10B981', '#F97316', '#0EA5E9', '#6366F1', '#F59E0B', '#EC4899', '#8B5CF6', '#14B8A6', '#F43F5E']
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader(L.CHART_ASSET_DIST)
        
        if not net_worth_data['by_symbol'].empty:
            # Apply currency conversion
            chart_data = net_worth_data['by_symbol'].copy()
            chart_data['value'] = chart_data['value'] * fx_rate
            
            # Use Treemap instead of Pie chart for better visual hierarchy
            fig_treemap = px.treemap(
                chart_data,
                path=['symbol'],
                values='value',
                title=L.CHART_BY_ASSET,
                color='value',
                color_continuous_scale=['#E0F2FE', '#0EA5E9', '#1E3A8A'],
            )
            
            fig_treemap.update_traces(
                texttemplate='<b>%{label}</b><br>%{value:,.0f} ' + cur_sym,
                textfont=dict(size=14),
                hovertemplate='%{label}<br>' + cur_sym + '%{value:,.0f}<br>%{percentParent:.1%}<extra></extra>'
            )
            
            fig_treemap.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False
            )
            
            st.plotly_chart(fig_treemap, use_container_width=True)
        else:
            st.info(L.CHART_NO_DATA)
    
    with col_chart2:
        st.subheader(L.CHART_ACCOUNT_DIST)
        
        if not net_worth_data['by_account'].empty:
            # Apply currency conversion
            chart_data = net_worth_data['by_account'].copy()
            chart_data['value'] = chart_data['value'] * fx_rate
            
            fig_account = px.pie(
                chart_data,
                values='value',
                names='account_name',
                title=L.CHART_BY_ACCOUNT,
                hole=0.6,
                color_discrete_sequence=MODERN_COLORS[::-1]
            )
            
            # Fix percentage format
            fig_account.update_traces(
                texttemplate='%{percent:.1%}',
                hovertemplate='%{label}<br>%{value:,.0f} ' + cur_sym + '<br>%{percent:.2%}<extra></extra>'
            )
            
            fig_account.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12)
            )
            
            st.plotly_chart(fig_account, use_container_width=True)
        else:
            st.info(L.CHART_NO_DATA)
    
    st.markdown("---")
    
    # History chart
    st.subheader(L.CHART_HISTORY)
    
    # Benchmark selector
    benchmark_options = ['S&P500', 'QQQ', 'BTC', '沪深300']
    selected_benchmarks = st.multiselect(
        "📊 对比基准",
        options=benchmark_options,
        default=[],
        help="选择要与您的资产组合进行对比的基准指数",
        placeholder="选择基准指数..."
    )
    
    history_df = get_net_worth_history()
    
    if not history_df.empty and len(history_df) > 1:
        # Apply time filter
        from datetime import timedelta
        history_df_filtered = history_df.copy()
        if time_filter == "7D":
            cutoff_date = date.today() - timedelta(days=7)
            history_df_filtered = history_df_filtered[history_df_filtered['date'] >= cutoff_date]
        elif time_filter == "30D":
            cutoff_date = date.today() - timedelta(days=30)
            history_df_filtered = history_df_filtered[history_df_filtered['date'] >= cutoff_date]
        elif time_filter == "90D":
            cutoff_date = date.today() - timedelta(days=90)
            history_df_filtered = history_df_filtered[history_df_filtered['date'] >= cutoff_date]
        
        # Apply currency conversion
        history_df_converted = history_df_filtered.copy()
        history_df_converted['net_worth'] = history_df_converted['net_worth'] * fx_rate
        
        # Check if we have enough data after filtering
        if len(history_df_converted) < 2:
            st.info(f"选定时间范围内数据不足，显示全部历史数据")
            history_df_converted = history_df.copy()
            history_df_converted['net_worth'] = history_df_converted['net_worth'] * fx_rate
        
        # Check if all values are the same (indicating missing historical prices)
        unique_values = history_df['net_worth'].nunique()
        
        if unique_values == 1:
            st.warning("📊 所有历史日期的净值相同，可能是因为缺少历史价格数据。建议在每次录入快照时同时更新价格，这样才能看到真实的净值变化曲线。")
        
        fig_history = go.Figure()
        
        # Determine trend color
        first_val = history_df_converted['net_worth'].iloc[0]
        last_val = history_df_converted['net_worth'].iloc[-1]
        is_up = last_val >= first_val
        
        if is_up:
            line_color = '#10B981'  # Green
            fill_color = 'rgba(16, 185, 129, 0.15)'
        else:
            line_color = '#EF4444'  # Red
            fill_color = 'rgba(239, 68, 68, 0.15)'
        
        # Check if we need benchmark comparison mode (percentage view)
        use_pct_view = len(selected_benchmarks) > 0
        
        if use_pct_view:
            # Calculate percentage change for portfolio
            history_df_converted['pct_change'] = ((history_df_converted['net_worth'] / first_val) - 1) * 100
            
            # Portfolio percentage line
            fig_history.add_trace(go.Scatter(
                x=history_df_converted['date'],
                y=history_df_converted['pct_change'],
                mode='lines+markers',
                name='我的组合',
                line=dict(color=line_color, width=3, shape='spline', smoothing=1.3),
                marker=dict(size=8, color='white', line=dict(color=line_color, width=2)),
                hovertemplate='<b>我的组合</b><br>%{y:.2f}%<extra></extra>'
            ))
            
            # Fetch and add benchmarks
            benchmark_colors = {
                'S&P500': '#6366F1',
                'QQQ': '#8B5CF6',
                'BTC': '#F59E0B',
                '沪深300': '#EF4444'
            }
            
            start_date = history_df_converted['date'].min()
            end_date = history_df_converted['date'].max()
            
            with st.spinner("📈 获取基准数据..."):
                benchmark_data = get_benchmark_history(start_date, end_date)
            
            for bench_name in selected_benchmarks:
                if bench_name in benchmark_data:
                    bench_df = benchmark_data[bench_name].copy()
                    
                    if len(bench_df) > 0:
                        bench_start = bench_df['price'].iloc[0]
                        bench_df['pct_change'] = ((bench_df['price'] / bench_start) - 1) * 100
                        
                        fig_history.add_trace(go.Scatter(
                            x=bench_df['date'],
                            y=bench_df['pct_change'],
                            mode='lines',
                            name=bench_name,
                            line=dict(
                                color=benchmark_colors.get(bench_name, '#9CA3AF'),
                                width=2,
                                dash='dot'
                            ),
                            hovertemplate=f'<b>{bench_name}</b><br>' + '%{y:.2f}%<extra></extra>'
                        ))
            
            # Show loading status
            loaded = [b for b in selected_benchmarks if b in benchmark_data]
            not_loaded = [b for b in selected_benchmarks if b not in benchmark_data]
            if loaded:
                st.caption(f"✅ 已加载: {', '.join(loaded)}")
            if not_loaded:
                st.caption(f"⚠️ 无法获取: {', '.join(not_loaded)}")
            
            # Calculate Y-axis range for percentage view
            all_pct = history_df_converted['pct_change'].tolist()
            for bench_name in selected_benchmarks:
                if bench_name in benchmark_data:
                    all_pct.extend(benchmark_data[bench_name]['pct_change'].tolist() if 'pct_change' in benchmark_data[bench_name].columns else [])
            
            y_min_pct = min(all_pct) if all_pct else -5
            y_max_pct = max(all_pct) if all_pct else 5
            y_padding = (y_max_pct - y_min_pct) * 0.15
            
            fig_history.update_layout(
                title=dict(text="<b>收益率对比</b>", font=dict(size=20, family='Outfit', color='#1F2937'), x=0, xanchor='left'),
                yaxis=dict(
                    title="收益率 %",
                    ticksuffix="%",
                    range=[y_min_pct - y_padding, y_max_pct + y_padding],
                    showgrid=True,
                    gridcolor='rgba(229, 231, 235, 0.6)',
                    griddash='dot',
                    zeroline=True,
                    zerolinecolor='#9CA3AF',
                    zerolinewidth=1
                )
            )
        else:
            # Original absolute value view (no benchmarks selected)
            y_min = history_df_converted['net_worth'].min()
            y_max = history_df_converted['net_worth'].max()
            y_range_padding = (y_max - y_min) * 0.15 if y_max != y_min else y_max * 0.05
            y_axis_min = max(0, y_min - y_range_padding)
            y_axis_max = y_max + y_range_padding
            
            # Fill area
            fig_history.add_trace(go.Scatter(
                x=history_df_converted['date'],
                y=history_df_converted['net_worth'],
                mode='lines',
                line=dict(color=line_color, width=4, shape='spline', smoothing=1.3),
                fill='tozeroy',
                fillcolor=fill_color,
                hoverinfo='skip',
                showlegend=False
            ))
            
            # Main line
            fig_history.add_trace(go.Scatter(
                x=history_df_converted['date'],
                y=history_df_converted['net_worth'],
                mode='lines+markers',
                name='我的组合',
                line=dict(color=line_color, width=3, shape='spline', smoothing=1.3),
                marker=dict(size=10, color='white', line=dict(color=line_color, width=3)),
                hovertemplate='<b>%{x}</b><br>' + cur_sym + '%{y:,.0f}<extra></extra>'
            ))
            
            # Add value annotations
            fig_history.add_annotation(
                x=history_df_converted['date'].iloc[0], y=first_val,
                text=f"{cur_sym}{first_val:,.0f}", showarrow=False, yshift=20,
                font=dict(size=11, color='#6B7280', family='Outfit'),
                bgcolor='rgba(255,255,255,0.8)', borderpad=4
            )
            fig_history.add_annotation(
                x=history_df_converted['date'].iloc[-1], y=last_val,
                text=f"<b>{cur_sym}{last_val:,.0f}</b>", showarrow=False, yshift=25,
                font=dict(size=13, color=line_color, family='Outfit'),
                bgcolor='rgba(255,255,255,0.9)', borderpad=4
            )
            
            fig_history.update_layout(
                title=dict(text=f"<b>{L.CHART_NW_OVER_TIME}</b>", font=dict(size=20, family='Outfit', color='#1F2937'), x=0, xanchor='left'),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(229, 231, 235, 0.6)',
                    griddash='dot',
                    zeroline=False,
                    range=[y_axis_min, y_axis_max],
                    tickprefix=cur_sym,
                    tickformat=',.0f',
                    side='right'
                )
            )
        
        # Common layout settings for both views
        chart_height = 480 if len(selected_benchmarks) > 0 else 420
        bottom_margin = 60 if len(selected_benchmarks) > 0 else 20
        
        fig_history.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=chart_height,
            margin=dict(l=20, r=20, t=70, b=bottom_margin),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False, 
                linecolor='#E5E7EB',
                tickfont=dict(size=11, color='#6B7280', family='Inter'),
                tickformat='%m/%d',
            ),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Inter',
                bordercolor='#E5E7EB'
            ),
            showlegend=len(selected_benchmarks) > 0,
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.12,
                xanchor='center',
                x=0.5,
                font=dict(size=10, family='Inter'),
                bgcolor='rgba(255,255,255,0.8)',
                itemsizing='constant',
                itemwidth=30
            )
        )
        
        st.plotly_chart(fig_history, use_container_width=True, config={'displayModeBar': False})
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            max_nw = history_df_converted['net_worth'].max()
            max_date = history_df_converted[history_df_converted['net_worth'] == max_nw]['date'].iloc[0]
            st.metric(L.CHART_ATH, f"{cur_sym}{max_nw:,.2f}", delta=f"{max_date}")
        
        with col_stat2:
            min_nw = history_df_converted['net_worth'].min()
            min_date = history_df_converted[history_df_converted['net_worth'] == min_nw]['date'].iloc[0]
            st.metric(L.CHART_ATL, f"{cur_sym}{min_nw:,.2f}", delta=f"{min_date}")
        
        with col_stat3:
            if len(history_df_converted) >= 2:
                growth = history_df_converted['net_worth'].iloc[-1] - history_df_converted['net_worth'].iloc[0]
                growth_pct = (growth / history_df_converted['net_worth'].iloc[0] * 100) if history_df_converted['net_worth'].iloc[0] > 0 else 0
                st.metric(L.CHART_GROWTH, f"{cur_sym}{growth:,.2f}", delta=f"{growth_pct:.2f}%")
    
    elif len(history_df) == 1:
        st.info(L.CHART_NEED_2)
    else:
        st.info(L.CHART_NO_HISTORY)
    
    st.markdown("---")
    
    # Monthly Returns Heatmap
    st.subheader("📅 月度收益热力图")
    
    if not history_df.empty and len(history_df) > 1:
        # Calculate monthly returns
        history_df_temp = history_df.copy()
        history_df_temp['date'] = pd.to_datetime(history_df_temp['date'])
        history_df_temp = history_df_temp.sort_values('date')
        
        # Group by month and get first/last values
        history_df_temp['year'] = history_df_temp['date'].dt.year
        history_df_temp['month'] = history_df_temp['date'].dt.month
        
        monthly_data = []
        for (year, month), group in history_df_temp.groupby(['year', 'month']):
            first_val = group['net_worth'].iloc[0]
            last_val = group['net_worth'].iloc[-1]
            ret = ((last_val - first_val) / first_val * 100) if first_val > 0 else 0
            monthly_data.append({'year': year, 'month': month, 'return': ret})
        
        monthly_df = pd.DataFrame(monthly_data)
        
        if not monthly_df.empty:
            # Pivot for heatmap
            months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
            
            pivot = monthly_df.pivot(index='year', columns='month', values='return')
            pivot = pivot.reindex(columns=range(1, 13), fill_value=None)
            pivot.columns = months
            
            # Create heatmap
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=months,
                y=pivot.index.astype(str),
                colorscale=[
                    [0, '#EF4444'],      # Red for negative
                    [0.5, '#F9FAFB'],    # White/gray for zero
                    [1, '#10B981']       # Green for positive
                ],
                zmid=0,
                text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                textfont={"size": 11, "color": "#1F2937"},
                hovertemplate="<b>%{y}年 %{x}</b><br>收益率: %{z:.2f}%<extra></extra>",
                showscale=True,
                colorbar=dict(
                    title=dict(text="收益率%", side="right"),
                    ticksuffix="%",
                    len=0.6
                )
            ))
            
            fig_heatmap.update_layout(
                height=180 + len(pivot) * 40,
                margin=dict(l=20, r=80, t=30, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    side='top',
                    tickfont=dict(size=11, color='#6B7280', family='Inter')
                ),
                yaxis=dict(
                    tickfont=dict(size=12, color='#1F2937', family='Outfit'),
                    autorange='reversed'
                )
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True, config={'displayModeBar': False})
            
            # Summary stats
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            positive_months = (monthly_df['return'] > 0).sum()
            negative_months = (monthly_df['return'] < 0).sum()
            total_months = len(monthly_df)
            avg_return = monthly_df['return'].mean()
            best_month = monthly_df.loc[monthly_df['return'].idxmax()]
            worst_month = monthly_df.loc[monthly_df['return'].idxmin()]
            
            with col_m1:
                st.metric("平均月收益", f"{avg_return:.2f}%")
            with col_m2:
                st.metric("盈利月份", f"{positive_months}/{total_months}", delta=f"{positive_months/total_months*100:.0f}%")
            with col_m3:
                st.metric("最佳月份", f"{int(best_month['year'])}/{int(best_month['month']):02d}", delta=f"+{best_month['return']:.2f}%")
            with col_m4:
                st.metric("最差月份", f"{int(worst_month['year'])}/{int(worst_month['month']):02d}", delta=f"{worst_month['return']:.2f}%")
    else:
        st.info("需要至少2个月的数据才能显示热力图")
    
    st.markdown("---")
    
    # Holdings detail
    st.subheader(L.HOLDINGS_DETAIL)
    
    if not net_worth_data['details'].empty:
        details_display = net_worth_data['details'].copy()
        details_display['quantity'] = details_display['quantity'].apply(lambda x: f"{x:,.8f}".rstrip('0').rstrip('.'))
        details_display['price'] = details_display['price'].apply(lambda x: f"{cur_sym}{x * fx_rate:,.2f}")
        details_display['value'] = details_display['value'].apply(lambda x: f"{cur_sym}{x * fx_rate:,.2f}")
        details_display = details_display[['account_name', 'symbol', 'quantity', 'price', 'value']]
        details_display.columns = [L.HOLDINGS_ACCOUNT, L.HOLDINGS_ASSET, L.HOLDINGS_QTY, L.HOLDINGS_PRICE, L.HOLDINGS_VALUE]
        
        st.dataframe(details_display, use_container_width=True, hide_index=True)
    else:
        st.info(L.HOLDINGS_NO_DATA)


# ============ Data Entry Page ============

def show_data_entry_page():
    """Data entry page"""
    
    st.markdown("---")
    st.header(L.ENTRY_TITLE)
    
    tab1, tab2 = st.tabs([L.ENTRY_SNAPSHOT, L.TRANSFER_TITLE])
    
    with tab1:
        st.subheader(L.ENTRY_SNAPSHOT)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"### {L.ENTRY_SETTINGS}")
            
            snapshot_date = st.date_input(
                L.ENTRY_DATE,
                value=date.today(),
                max_value=date.today(),
                help=L.ENTRY_SNAPSHOT_DATE
            )
            
            existing_accounts = get_unique_accounts()
            
            # Get account balances for sorting and display
            net_worth_data = calculate_current_net_worth()
            account_balances = {}
            if not net_worth_data['by_account'].empty:
                for _, row in net_worth_data['by_account'].iterrows():
                    account_balances[row['account_name']] = row['value']
            
            # Sort accounts by balance (highest first), then alphabetically for zero-balance
            def get_sort_key(acc):
                bal = account_balances.get(acc, 0)
                return (-bal, acc)  # Negative for descending balance, then alphabetical
            
            sorted_accounts = sorted(existing_accounts, key=get_sort_key)
            
            # Create display options with balance info
            account_display_map = {}
            account_options = []
            for acc in sorted_accounts:
                bal = account_balances.get(acc, 0)
                if bal >= 1:
                    display = f"{acc}  💰 ${bal:,.0f}"
                else:
                    display = f"{acc}  ⚪ $0"
                account_display_map[display] = acc
                account_options.append(display)
            
            if existing_accounts:
                account_input_method = st.radio(
                    L.ENTRY_ACCOUNT,
                    [L.ENTRY_SELECT_EXISTING, L.ENTRY_NEW_ACCOUNT],
                    horizontal=True
                )
                
                if account_input_method == L.ENTRY_SELECT_EXISTING:
                    selected_display = st.selectbox(
                        L.ENTRY_ACCOUNT,
                        options=account_options,
                        help=f"{L.ENTRY_SELECT_EXISTING}{L.ENTRY_ACCOUNT}（按余额排序）",
                        key='account_select'
                    )
                    account_name = account_display_map.get(selected_display, selected_display.split("  ")[0])
                    
                    # Auto-load previous holdings when account changes
                    prev_account = st.session_state.get('_prev_account', None)
                    if account_name != prev_account:
                        st.session_state['_prev_account'] = account_name
                        
                        # Load holdings for this account
                        session = get_session(engine)
                        try:
                            latest = session.query(Snapshot).filter(
                                Snapshot.account_name == account_name
                            ).order_by(Snapshot.date.desc()).first()
                            
                            if latest:
                                latest_date = latest.date
                                latest_holdings = session.query(Snapshot).filter(
                                    and_(
                                        Snapshot.account_name == account_name,
                                        Snapshot.date == latest_date
                                    )
                                ).all()
                                
                                if latest_holdings:
                                    st.session_state.snapshot_data = pd.DataFrame({
                                        'Symbol': [h.symbol for h in latest_holdings] + [''],
                                        'Quantity': [h.quantity for h in latest_holdings] + [0.0]
                                    })
                                    st.toast(f"📥 已加载 {account_name} 的 {len(latest_holdings)} 条持仓", icon="✅")
                        finally:
                            session.close()
                else:
                    account_name = st.text_input(
                        L.ENTRY_ACCOUNT_NAME,
                        placeholder=L.ENTRY_ACCOUNT_HINT,
                        help=f"{L.ENTRY_NEW_ACCOUNT}{L.ENTRY_ACCOUNT_NAME}"
                    )
            else:
                account_name = st.text_input(
                    L.ENTRY_ACCOUNT_NAME,
                    placeholder=L.ENTRY_ACCOUNT_HINT,
                    help=f"{L.ENTRY_ENTER_ACCOUNT}"
                )
            
            st.info(f"{L.ENTRY_CURRENT_ACCOUNT}: **{account_name or L.ENTRY_NONE}**")
        
        with col2:
            st.markdown(f"### {L.ENTRY_HOLDINGS}")
            
            if 'snapshot_data' not in st.session_state:
                st.session_state.snapshot_data = pd.DataFrame({
                    'Symbol': ['BTC', 'ETH', ''],
                    'Quantity': [0.0, 0.0, 0.0]
                })
            
            edited_data = st.data_editor(
                st.session_state.snapshot_data,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    'Symbol': st.column_config.TextColumn(
                        L.ENTRY_SYMBOL,
                        help=L.ENTRY_SYMBOL_HINT,
                        width='medium'
                    ),
                    'Quantity': st.column_config.NumberColumn(
                        L.ENTRY_QUANTITY,
                        help=L.ENTRY_QTY_HELP,
                        min_value=0.0,
                        format="%.8f",
                        width='medium'
                    )
                },
                hide_index=True,
                key='snapshot_editor'
            )
            
            valid_rows = edited_data[
                (edited_data['Symbol'].astype(str).str.strip() != '') & 
                (edited_data['Quantity'] > 0)
            ]
            st.caption(f"{L.ENTRY_VALID_ROWS}: {len(valid_rows)}")
        
        col_btn1, col_btn2, _ = st.columns([1, 1, 2])
        
        with col_btn1:
            save_snapshot_btn = st.button(L.ENTRY_SAVE_SNAPSHOT, type="primary", use_container_width=True)
        
        with col_btn2:
            clear_table_btn = st.button(L.ENTRY_CLEAR, use_container_width=True)
        
        if clear_table_btn:
            st.session_state.snapshot_data = pd.DataFrame({
                'Symbol': [''],
                'Quantity': [0.0]
            })
            st.rerun()
        
        if save_snapshot_btn:
            if not account_name or account_name.strip() == '':
                st.error(L.ENTRY_ENTER_ACCOUNT)
            else:
                valid_rows = edited_data[
                    (edited_data['Symbol'].astype(str).str.strip() != '') & 
                    (edited_data['Quantity'] > 0)
                ]
                
                if len(valid_rows) == 0:
                    st.warning(L.ENTRY_NO_VALID)
                else:
                    try:
                        # 1. Save current account's snapshot
                        count = save_snapshots_batch(snapshot_date, account_name, valid_rows)
                        
                        # 2. Auto carry-forward other accounts from previous date
                        session = get_session(engine)
                        try:
                            # Find accounts that exist on previous dates but not on current date
                            prev_date = session.query(Snapshot.date).filter(
                                Snapshot.date < snapshot_date
                            ).order_by(Snapshot.date.desc()).first()
                            
                            carried_count = 0
                            if prev_date:
                                # Get all accounts from previous date
                                prev_snapshots = session.query(Snapshot).filter(
                                    Snapshot.date == prev_date[0]
                                ).all()
                                
                                for old_snap in prev_snapshots:
                                    # Skip if it's the account we just saved
                                    if old_snap.account_name == account_name:
                                        continue
                                    
                                    # Check if already exists for new date
                                    existing = session.query(Snapshot).filter(
                                        and_(
                                            Snapshot.date == snapshot_date,
                                            Snapshot.account_name == old_snap.account_name,
                                            Snapshot.symbol == old_snap.symbol
                                        )
                                    ).first()
                                    
                                    if not existing:
                                        new_snap = Snapshot(
                                            date=snapshot_date,
                                            account_name=old_snap.account_name,
                                            symbol=old_snap.symbol,
                                            quantity=old_snap.quantity
                                        )
                                        session.add(new_snap)
                                        carried_count += 1
                                
                                if carried_count > 0:
                                    session.commit()
                                    clear_data_cache()
                        finally:
                            session.close()
                        
                        # Show success message
                        msg = L.ENTRY_SAVED_N.format(count)
                        if carried_count > 0:
                            msg += f" (自动继承其他账户 {carried_count} 条)"
                        st.success(msg)
                        st.balloons()
                        st.session_state.snapshot_data = edited_data
                        
                    except Exception as e:
                        st.error(f"{L.ENTRY_SAVE_FAILED}: {e}")
    
    with tab2:
        st.subheader(L.TRANSFER_TITLE)
        
        with st.form("transfer_form"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                transfer_date = st.date_input(
                    L.ENTRY_DATE,
                    value=date.today(),
                    max_value=date.today()
                )
            
            with col2:
                transfer_type = st.selectbox(
                    L.TRANSFER_TYPE,
                    ["deposit", "withdrawal"],
                    format_func=lambda x: L.TRANSFER_DEPOSIT if x == "deposit" else L.TRANSFER_WITHDRAWAL
                )
            
            with col3:
                amount_usd = st.number_input(
                    L.TRANSFER_AMOUNT,
                    min_value=0.0,
                    step=100.0,
                    format="%.2f"
                )
            
            with col4:
                note = st.text_input(
                    L.TRANSFER_NOTE,
                    placeholder=L.TRANSFER_OPTIONAL
                )
            
            submitted = st.form_submit_button(L.TRANSFER_SAVE, type="primary", use_container_width=True)
            
            if submitted:
                if amount_usd <= 0:
                    st.error(L.TRANSFER_AMOUNT_GT0)
                else:
                    try:
                        save_transfer(transfer_date, transfer_type, amount_usd, note)
                        type_str = L.TRANSFER_DEPOSIT if transfer_type == "deposit" else L.TRANSFER_WITHDRAWAL
                        st.success(L.TRANSFER_SAVED.format(type_str, amount_usd))
                    except Exception as e:
                        st.error(f"{L.ENTRY_SAVE_FAILED}: {e}")


# ============ Price Page ============

def show_price_page():
    """Price update page"""
    
    st.markdown("---")
    st.header(L.PRICE_TITLE)
    
    tab1, tab2 = st.tabs([L.PRICE_AUTO, L.PRICE_MANUAL])
    
    with tab1:
        st.subheader(L.PRICE_AUTO)
        
        session_db = get_session(engine)
        try:
            snapshots = session_db.query(Snapshot.symbol).distinct().order_by(Snapshot.symbol).all()
            symbols_from_snapshots = [s[0] for s in snapshots]
        finally:
            session_db.close()
        
        if not symbols_from_snapshots:
            st.warning(L.PRICE_NO_SNAPSHOTS)
        else:
            st.info(L.PRICE_FOUND_N.format(len(symbols_from_snapshots), ', '.join(symbols_from_snapshots)))
            
            input_method = st.radio(
                L.PRICE_SOURCE,
                [L.PRICE_FROM_SNAPSHOTS, L.PRICE_CUSTOM],
                horizontal=True
            )
            
            if input_method == L.PRICE_FROM_SNAPSHOTS:
                symbols_to_fetch = symbols_from_snapshots
                st.success(L.PRICE_WILL_FETCH.format(len(symbols_to_fetch)))
            else:
                symbols_input = st.text_area(
                    L.PRICE_SYMBOLS_HINT,
                    value="\n".join(symbols_from_snapshots),
                    height=150
                )
                symbols_to_fetch = [s.strip().upper() for s in symbols_input.split('\n') if s.strip()]
            
            if st.button(L.PRICE_FETCH, type="primary", use_container_width=True):
                if not symbols_to_fetch:
                    st.error(L.PRICE_NO_SYMBOLS)
                else:
                    with st.spinner(L.PRICE_FETCHING.format(len(symbols_to_fetch))):
                        try:
                            count = price_service.update_price_history_db(symbols_to_fetch)
                            clear_data_cache()  # Invalidate cache after price update
                            st.success(L.PRICE_UPDATED_N.format(count))
                            st.balloons()
                            
                            session_db = get_session(engine)
                            try:
                                prices = session_db.query(PriceHistory).filter(
                                    PriceHistory.date == date.today()
                                ).all()
                                
                                if prices:
                                    price_data = [{
                                        L.PRICE_SYMBOL: p.symbol,
                                        L.PRICE_PRICE: f"${p.price_usd:,.4f}",
                                        L.PRICE_SOURCE: p.source or 'manual'
                                    } for p in prices]
                                    
                                    st.dataframe(pd.DataFrame(price_data), use_container_width=True, hide_index=True)
                            finally:
                                session_db.close()
                            
                        except Exception as e:
                            st.error(f"{L.PRICE_FETCH_FAILED}: {e}")
    
    with tab2:
        st.subheader(L.PRICE_MANUAL)
        
        with st.form("manual_price_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                price_date = st.date_input(
                    L.ENTRY_DATE,
                    value=date.today(),
                    max_value=date.today()
                )
            
            with col2:
                symbol = st.text_input(
                    L.PRICE_SYMBOL,
                    placeholder="BTC, ETH..."
                ).strip().upper()
            
            with col3:
                price_usd = st.number_input(
                    L.PRICE_PRICE,
                    min_value=0.0,
                    step=0.0001,
                    format="%.4f"
                )
            
            submitted = st.form_submit_button(L.PRICE_SAVE, type="primary", use_container_width=True)
            
            if submitted:
                if not symbol:
                    st.error(L.PRICE_ENTER_SYMBOL)
                elif price_usd <= 0:
                    st.error(L.PRICE_GT0)
                else:
                    session = get_session(engine)
                    try:
                        existing = session.query(PriceHistory).filter(
                            and_(
                                PriceHistory.date == price_date,
                                PriceHistory.symbol == symbol
                            )
                        ).first()
                        
                        if existing:
                            existing.price_usd = price_usd
                            existing.source = 'manual'
                            existing.created_at = datetime.utcnow()
                        else:
                            new_price = PriceHistory(
                                date=price_date,
                                symbol=symbol,
                                price_usd=price_usd,
                                source='manual'
                            )
                            session.add(new_price)
                        
                        session.commit()
                        clear_data_cache()  # Invalidate cache after manual price entry
                        st.success(L.PRICE_SAVED.format(symbol, price_usd))
                        
                    except Exception as e:
                        session.rollback()
                        st.error(f"{L.PRICE_SAVE_FAILED}: {e}")
                    finally:
                        session.close()


# ============ Data View Page ============

def show_data_view_page():
    """Data view page"""
    
    st.markdown("---")
    st.header(L.VIEW_TITLE)
    
    # Initialize archived accounts in session state
    if 'archived_accounts' not in st.session_state:
        st.session_state['archived_accounts'] = []
    
    # Account Management Section
    st.markdown("##### 📦 账户管理")
    
    existing_accounts = get_unique_accounts()
    active_accounts = [a for a in existing_accounts if a not in st.session_state['archived_accounts']]
    archived_accounts = [a for a in existing_accounts if a in st.session_state['archived_accounts']]
    
    # Archive account
    if active_accounts:
        st.markdown("###### 隐藏账户 (历史数据保留)")
        hide_col1, hide_col2 = st.columns([3, 1])
        
        with hide_col1:
            account_to_hide = st.selectbox(
                "选择要隐藏的账户",
                options=[""] + active_accounts,
                index=0,
                label_visibility="collapsed",
                placeholder="选择账户...",
                key="hide_account_select"
            )
        
        with hide_col2:
            if account_to_hide and st.button("📦 隐藏", use_container_width=True):
                st.session_state['archived_accounts'].append(account_to_hide)
                clear_data_cache()
                st.success(f"✅ 已隐藏账户 {account_to_hide}（历史数据已保留）")
                st.rerun()
    
    # Restore archived account
    if archived_accounts:
        st.markdown("###### 已隐藏的账户")
        for acc in archived_accounts:
            restore_col1, restore_col2 = st.columns([3, 1])
            with restore_col1:
                st.text(f"📦 {acc}")
            with restore_col2:
                if st.button("🔄 恢复", key=f"restore_{acc}", use_container_width=True):
                    st.session_state['archived_accounts'].remove(acc)
                    clear_data_cache()
                    st.success(f"✅ 已恢复账户 {acc}")
                    st.rerun()
    
    if not existing_accounts:
        st.info("暂无账户数据")
    
    st.markdown("---")
    
    # Export section
    st.markdown("##### 📥 数据导出")
    export_col1, export_col2, export_col3, _ = st.columns([1, 1, 1, 1])
    
    with export_col1:
        session = get_session(engine)
        try:
            all_snapshots = session.query(Snapshot).order_by(Snapshot.date.desc()).all()
            if all_snapshots:
                snapshot_df = pd.DataFrame([{
                    '日期': s.date,
                    '账户': s.account_name,
                    '币种': s.symbol,
                    '数量': s.quantity
                } for s in all_snapshots])
                csv = snapshot_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 导出快照",
                    csv,
                    "snapshots.csv",
                    "text/csv",
                    use_container_width=True
                )
        finally:
            session.close()
    
    with export_col2:
        session = get_session(engine)
        try:
            all_transfers = session.query(Transfer).order_by(Transfer.date.desc()).all()
            if all_transfers:
                transfer_df = pd.DataFrame([{
                    '日期': t.date,
                    '类型': '入金' if t.type == 'deposit' else '出金',
                    '金额': t.amount_usd,
                    '备注': t.note or ''
                } for t in all_transfers])
                csv = transfer_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "💸 导出转账",
                    csv,
                    "transfers.csv",
                    "text/csv",
                    use_container_width=True
                )
        finally:
            session.close()
    
    with export_col3:
        session = get_session(engine)
        try:
            all_prices = session.query(PriceHistory).order_by(PriceHistory.date.desc()).all()
            if all_prices:
                price_df = pd.DataFrame([{
                    '日期': p.date,
                    '币种': p.symbol,
                    '价格': p.price_usd,
                    '来源': p.source or 'manual'
                } for p in all_prices])
                csv = price_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "💰 导出价格",
                    csv,
                    "prices.csv",
                    "text/csv",
                    use_container_width=True
                )
        finally:
            session.close()
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs([L.VIEW_SNAPSHOTS, L.VIEW_TRANSFERS, L.VIEW_PRICES])
    
    with tab1:
        st.subheader(L.VIEW_RECENT + " " + L.VIEW_SNAPSHOTS)
        snapshots = get_recent_snapshots(20)
        
        if snapshots:
            data = [{
                L.ENTRY_DATE: s.date,
                L.ENTRY_ACCOUNT: s.account_name,
                L.ENTRY_SYMBOL: s.symbol,
                L.ENTRY_QUANTITY: f"{s.quantity:,.8f}".rstrip('0').rstrip('.')
            } for s in snapshots]
            
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info(L.VIEW_NO_DATA)
    
    with tab2:
        st.subheader(L.VIEW_RECENT + " " + L.VIEW_TRANSFERS)
        transfers = get_recent_transfers(20)
        
        if transfers:
            data = [{
                L.ENTRY_DATE: t.date,
                L.TRANSFER_TYPE: L.TRANSFER_DEPOSIT if t.type == "deposit" else L.TRANSFER_WITHDRAWAL,
                L.TRANSFER_AMOUNT: f"${t.amount_usd:,.2f}",
                L.TRANSFER_NOTE: t.note or ''
            } for t in transfers]
            
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info(L.VIEW_NO_DATA)
    
    with tab3:
        st.subheader(L.VIEW_RECENT + " " + L.VIEW_PRICES)
        session = get_session(engine)
        try:
            prices = session.query(PriceHistory).order_by(
                PriceHistory.date.desc()
            ).limit(50).all()
            
            if prices:
                data = [{
                    L.ENTRY_DATE: p.date,
                    L.PRICE_SYMBOL: p.symbol,
                    L.PRICE_PRICE: f"${p.price_usd:,.4f}",
                    L.VIEW_SOURCE: p.source or 'manual'
                } for p in prices]
                
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info(L.VIEW_NO_DATA)
        finally:
            session.close()


# ============ Tips Page ============

def show_tips_page():
    """Tips page"""
    
    st.markdown("---")
    st.header(L.TIPS_TITLE)
    
    st.markdown(L.TIPS_CONTENT)


# ============ Entry Point ============

if __name__ == '__main__':
    main()
