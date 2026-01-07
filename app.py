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

# ============ Database Functions ============

def save_snapshots_batch(snapshot_date, account_name, snapshot_data):
    """Save batch snapshots"""
    session = get_session(engine)
    saved_count = 0
    
    try:
        for _, row in snapshot_data.iterrows():
            symbol = str(row['Symbol']).strip().upper()
            quantity = float(row['Quantity'])
            
            if not symbol or symbol == '' or quantity <= 0:
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
        
        if total_hours > 0 and roi > -100:
            apy = (((1 + roi/100) ** (hours_per_year / total_hours)) - 1) * 100
        else:
            apy = 0
        
        return {
            'has_data': True,
            'roi': roi,
            'apy': apy,
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
        
        # Privacy Toggle
        privacy_on = st.toggle("🔒 隐私模式", value=st.session_state.get('privacy_mode', False))
        st.session_state['privacy_mode'] = privacy_on
        
        # Side Navigation
        page = st.radio(
            "Menu", # This will be hidden by CSS
            [L.NAV_DASHBOARD, L.NAV_DATA_ENTRY, L.NAV_PRICE_UPDATE, L.NAV_DATA_VIEW],
            index=0
        )
        
        st.markdown("<div style='flex-grow:1; height: 100px;'></div>", unsafe_allow_html=True)
        
        # Bottom Stats Card
        st.markdown('<div class="side-stats">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:0.65rem; font-weight:700; color:#9CA3AF; text-transform:uppercase; margin-bottom:12px;">{L.SIDEBAR_STATS}</div>', unsafe_allow_html=True)
        session = get_session(engine)
        try:
            snapshot_count = session.query(Snapshot).count()
            transfer_count = session.query(Transfer).count()
            price_count = session.query(PriceHistory).count()
            
            for lab, val in [(L.STAT_SNAPSHOTS, snapshot_count), (L.STAT_TRANSFERS, transfer_count), (L.STAT_PRICES, price_count)]:
                st.markdown(f'<div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span style="color:#6B7280; font-size:0.75rem;">{lab}</span><span style="font-weight:700; font-size:0.75rem;">{val}</span></div>', unsafe_allow_html=True)
        finally:
            session.close()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Dashboard logic with Benchmarking
    if page == L.NAV_DASHBOARD:
        show_dashboard(privacy_on)
    elif page == L.NAV_DATA_ENTRY:
        show_data_entry_page()
    elif page == L.NAV_PRICE_UPDATE:
        show_price_page()
    elif page == L.NAV_DATA_VIEW:
        show_data_view_page()


# ============ Dashboard Calculations (Cached) ============

def show_dashboard(privacy_on=False):
    """Dashboard page with Benchmarking"""
    st.markdown("---")
    
    net_worth_data = calculate_current_net_worth()
    transfers_data = calculate_transfers_summary()
    pnl_data = calculate_pnl()
    time_returns = calculate_time_based_returns()
    
    # Quick Benchmark (BTC ROI since first snapshot)
    benchmark_roi = 0.0
    try:
        session = get_session(engine)
        first_snapshot = session.query(Snapshot.date).order_by(Snapshot.date.asc()).first()
        if first_snapshot:
            # Get latest BTC and BTC at first snapshot date
            btc_current = session.query(PriceHistory.price_usd).filter(PriceHistory.symbol=='BTC').order_by(PriceHistory.date.desc()).first()
            btc_start = session.query(PriceHistory.price_usd).filter(PriceHistory.symbol=='BTC', PriceHistory.date <= first_snapshot[0]).order_by(PriceHistory.date.desc()).first()
            if btc_current and btc_start and btc_start[0] > 0:
                benchmark_roi = ((btc_current[0] / btc_start[0]) - 1) * 100
        session.close()
    except:
        pass

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
        value=f"${net_worth_data['total_net_worth']:,.2f}",
        is_masked=privacy_on
    )
    
    # Other metrics in one row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        S.metric_card(
            label=L.DASH_INVESTED,
            value=f"${transfers_data['net_investment']:,.2f}",
            delta=f"${transfers_data['total_deposits']:,.0f} 入 | ${transfers_data['total_withdrawals']:,.0f} 出",
            delta_up="neutral",
            is_masked=privacy_on
        )
    
    with col2:
        pnl_value = pnl_data['unrealized_pnl']
        S.metric_card(
            label=L.DASH_PNL,
            value=f"${pnl_value:,.2f}",
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
        
        col_time1, col_time2, col_time3 = st.columns(3)
        
        with col_time1:
            st.info(f"""
            **{L.TIME_PERIOD}**  
            {L.TIME_START}: {time_returns['start_date']}  
            {L.TIME_END}: {time_returns['end_date']}  
            {L.TIME_DAYS}: {time_returns['days']:.1f}  
            {L.TIME_HOURS}: {time_returns['hours']:.1f}
            """)
        
        with col_time2:
            st.info(f"""
            **{L.TIME_NW_CHANGE}**  
            {L.TIME_START}: ${time_returns['start_net_worth']:,.2f}  
            {L.TIME_END}: ${time_returns['end_net_worth']:,.2f}  
            {L.TIME_CHANGE}: ${time_returns['end_net_worth'] - time_returns['start_net_worth']:,.2f}
            """)
        
        with col_time3:
            st.info(f"""
            **{L.TIME_CASH_FLOW}**  
            {L.TIME_DEPOSITS}: ${time_returns.get('period_deposits', 0):,.2f}  
            {L.TIME_WITHDRAWALS}: ${time_returns.get('period_withdrawals', 0):,.2f}  
            {L.TIME_NET}: ${time_returns['net_cash_flow']:,.2f}
            """)
        
        col_apy1, col_apy2 = st.columns(2)
        
        with col_apy1:
            st.metric(
                label=L.TIME_PERIOD_ROI,
                value=f"{time_returns['roi']:.2f}%",
                delta=f"{time_returns['hours']:.1f} {L.TIME_HOURS}",
                delta_color="normal" if time_returns['roi'] >= 0 else "inverse"
            )
        
        with col_apy2:
            st.metric(
                label=L.TIME_APY,
                value=f"{time_returns['apy']:,.2f}%",
                delta=L.TIME_ANNUALIZED if abs(time_returns['apy']) < 1000 else L.TIME_HIGH_VOL,
                delta_color="normal" if time_returns['apy'] >= 0 else "inverse"
            )
    
    st.markdown("---")
    
    # Charts
    if net_worth_data['details'].empty or net_worth_data['details']['price'].sum() == 0:
        st.warning(L.CHART_MISSING_PRICE)
    
    # Falcon Finance Colors: Emerald (USDT style), Orange, Blue, Indigo, Amber
    MODERN_COLORS = ['#10B981', '#F97316', '#0EA5E9', '#6366F1', '#F59E0B', '#EC4899', '#8B5CF6']
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader(L.CHART_ASSET_DIST)
        
        if not net_worth_data['by_symbol'].empty:
            fig_symbol = px.pie(
                net_worth_data['by_symbol'],
                values='value',
                names='symbol',
                title=L.CHART_BY_ASSET,
                hole=0.6,
                color_discrete_sequence=MODERN_COLORS
            )
            
            fig_symbol.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12),
                showlegend=True
            )
            
            st.plotly_chart(fig_symbol, use_container_width=True)
        else:
            st.info(L.CHART_NO_DATA)
    
    with col_chart2:
        st.subheader(L.CHART_ACCOUNT_DIST)
        
        if not net_worth_data['by_account'].empty:
            fig_account = px.pie(
                net_worth_data['by_account'],
                values='value',
                names='account_name',
                title=L.CHART_BY_ACCOUNT,
                hole=0.6,
                color_discrete_sequence=MODERN_COLORS[::-1]
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
    
    history_df = get_net_worth_history()
    
    if not history_df.empty and len(history_df) > 1:
        fig_history = go.Figure()
        
        fig_history.add_trace(go.Scatter(
            x=history_df['date'],
            y=history_df['net_worth'],
            mode='lines',
            name=L.DASH_NET_WORTH,
            line=dict(color='#000000', width=4, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(0, 0, 0, 0.03)'
        ))
        
        fig_history.update_layout(
            title=dict(text=L.CHART_NW_OVER_TIME, font=dict(size=18, family='Outfit')),
            xaxis_title=None,
            yaxis_title=None,
            height=400,
            margin=dict(l=0, r=0, t=60, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, linecolor='#E5E7EB'),
            yaxis=dict(showgrid=True, gridcolor='#F3F4F6', zeroline=False)
        )
        
        st.plotly_chart(fig_history, use_container_width=True)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            max_nw = history_df['net_worth'].max()
            max_date = history_df[history_df['net_worth'] == max_nw]['date'].iloc[0]
            st.metric(L.CHART_ATH, f"${max_nw:,.2f}", delta=f"{max_date}")
        
        with col_stat2:
            min_nw = history_df['net_worth'].min()
            min_date = history_df[history_df['net_worth'] == min_nw]['date'].iloc[0]
            st.metric(L.CHART_ATL, f"${min_nw:,.2f}", delta=f"{min_date}")
        
        with col_stat3:
            if len(history_df) >= 2:
                growth = history_df['net_worth'].iloc[-1] - history_df['net_worth'].iloc[0]
                growth_pct = (growth / history_df['net_worth'].iloc[0] * 100) if history_df['net_worth'].iloc[0] > 0 else 0
                st.metric(L.CHART_GROWTH, f"${growth:,.2f}", delta=f"{growth_pct:.2f}%")
    
    elif len(history_df) == 1:
        st.info(L.CHART_NEED_2)
    else:
        st.info(L.CHART_NO_HISTORY)
    
    st.markdown("---")
    
    # Holdings detail
    st.subheader(L.HOLDINGS_DETAIL)
    
    if not net_worth_data['details'].empty:
        details_display = net_worth_data['details'].copy()
        details_display['quantity'] = details_display['quantity'].apply(lambda x: f"{x:,.8f}".rstrip('0').rstrip('.'))
        details_display['price'] = details_display['price'].apply(lambda x: f"${x:,.2f}")
        details_display['value'] = details_display['value'].apply(lambda x: f"${x:,.2f}")
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
            
            if existing_accounts:
                account_input_method = st.radio(
                    L.ENTRY_ACCOUNT,
                    [L.ENTRY_SELECT_EXISTING, L.ENTRY_NEW_ACCOUNT],
                    horizontal=True
                )
                
                if account_input_method == L.ENTRY_SELECT_EXISTING:
                    account_name = st.selectbox(
                        L.ENTRY_ACCOUNT,
                        options=existing_accounts,
                        help=f"{L.ENTRY_SELECT_EXISTING}{L.ENTRY_ACCOUNT}"
                    )
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
                        count = save_snapshots_batch(snapshot_date, account_name, valid_rows)
                        st.success(L.ENTRY_SAVED_N.format(count))
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
        
        session_db = get_session(get_engine())
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
                            st.success(L.PRICE_UPDATED_N.format(count))
                            st.balloons()
                            
                            session_db = get_session(get_engine())
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
                    session = get_session(get_engine())
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
