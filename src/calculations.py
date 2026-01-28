"""
Business calculations module
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import desc
from sqlalchemy.orm import sessionmaker

from src.models import Snapshot, Transfer, PriceHistory
from src.database import get_session, get_price_for_date, get_latest_snapshot_date


@st.cache_data(ttl=600)
def calculate_net_worth_for_date(_engine, target_date):
    """Calculate net worth for a specific date"""
    session = get_session(_engine)
    
    try:
        snapshots = session.query(Snapshot).filter(Snapshot.date == target_date).all()
        
        if not snapshots:
            return pd.DataFrame()
        
        data = []
        for s in snapshots:
            price = get_price_for_date(_engine, s.symbol, target_date)
            value = s.quantity * price
            data.append({
                'account_name': s.account_name,
                'symbol': s.symbol,
                'quantity': s.quantity,
                'price': price,
                'value': value
            })
        
        return pd.DataFrame(data)
        
    finally:
        session.close()


@st.cache_data(ttl=600)
def calculate_current_net_worth(_engine):
    """Calculate current net worth"""
    latest_date = get_latest_snapshot_date(_engine)
    
    if not latest_date:
        return {
            'total_net_worth': 0,
            'latest_date': None,
            'by_symbol': pd.DataFrame(),
            'by_account': pd.DataFrame(),
            'details': pd.DataFrame()
        }
    
    details_df = calculate_net_worth_for_date(_engine, latest_date)
    
    if details_df.empty:
        return {
            'total_net_worth': 0,
            'latest_date': latest_date,
            'by_symbol': pd.DataFrame(),
            'by_account': pd.DataFrame(),
            'details': pd.DataFrame()
        }
    
    total = details_df['value'].sum()
    by_symbol = details_df.groupby('symbol').agg({'quantity': 'sum', 'value': 'sum'}).reset_index()
    by_account = details_df.groupby('account_name').agg({'value': 'sum'}).reset_index()
    
    return {
        'total_net_worth': total,
        'latest_date': latest_date,
        'by_symbol': by_symbol,
        'by_account': by_account,
        'details': details_df
    }


@st.cache_data(ttl=600)
def calculate_transfers_summary(_engine):
    """Calculate transfers summary"""
    session = get_session(_engine)
    
    try:
        transfers = session.query(Transfer).all()
        
        total_deposits = sum(t.amount_usd for t in transfers if t.type == 'deposit')
        total_withdrawals = sum(t.amount_usd for t in transfers if t.type == 'withdrawal')
        net_flow = total_deposits - total_withdrawals
        
        return {
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'net_investment': net_flow,
            'net_flow': net_flow
        }
        
    finally:
        session.close()


@st.cache_data(ttl=600)
def calculate_pnl(_engine):
    """Calculate PnL"""
    net_worth_data = calculate_current_net_worth(_engine)
    transfers_data = calculate_transfers_summary(_engine)
    
    total_net_worth = net_worth_data['total_net_worth']
    net_flow = transfers_data['net_flow']
    
    pnl = total_net_worth - net_flow
    pnl_pct = (pnl / net_flow * 100) if net_flow > 0 else 0
    
    return {
        'unrealized_pnl': pnl,
        'roi_percentage': pnl_pct,
        'net_worth': total_net_worth,
        'cost_basis': net_flow
    }


@st.cache_data(ttl=600)
def calculate_time_based_returns(_engine):
    """Calculate time-based returns and APY"""
    session = get_session(_engine)
    
    try:
        # Get first and last snapshot dates
        dates = session.query(Snapshot.date).distinct().order_by(Snapshot.date).all()
        dates = [d[0] for d in dates]
        
        if len(dates) < 2:
            return {'has_data': False}
        
        start_date = dates[0]
        end_date = dates[-1]
        
        # Calculate start and end net worth
        start_net_worth = calculate_net_worth_for_date(_engine, start_date)['value'].sum() if not calculate_net_worth_for_date(_engine, start_date).empty else 0
        end_net_worth = calculate_net_worth_for_date(_engine, end_date)['value'].sum() if not calculate_net_worth_for_date(_engine, end_date).empty else 0
        
        if start_net_worth == 0:
            return {'has_data': False}
        
        # Get transfers in period
        transfers = session.query(Transfer).filter(
            Transfer.date >= start_date,
            Transfer.date <= end_date
        ).all()
        
        period_deposits = sum(t.amount_usd for t in transfers if t.type == 'deposit')
        period_withdrawals = sum(t.amount_usd for t in transfers if t.type == 'withdrawal')
        net_cash_flow = period_deposits - period_withdrawals
        
        # Time-weighted calculation
        total_days = (end_date - start_date).days
        total_hours = total_days * 24
        
        if total_days == 0:
            return {'has_data': False}
        
        # Simple ROI
        adjusted_end = end_net_worth - net_cash_flow
        roi = ((adjusted_end / start_net_worth) - 1) * 100
        
        # Annualized returns
        years = total_days / 365
        apr = roi / years if years > 0 else roi
        apy = ((1 + roi/100) ** (1/years) - 1) * 100 if years > 0 else roi
        
        return {
            'has_data': True,
            'roi': roi,
            'apr': apr,
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


@st.cache_data(ttl=600)
def get_net_worth_history(_engine):
    """Get net worth history"""
    session = get_session(_engine)
    
    try:
        dates = session.query(Snapshot.date).distinct().order_by(Snapshot.date).all()
        dates = [d[0] for d in dates]
        
        if not dates:
            return pd.DataFrame()
        
        history = []
        for d in dates:
            net_worth_df = calculate_net_worth_for_date(_engine, d)
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
                # Handle multi-level columns
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                prices = data[['Close']].reset_index()
                prices.columns = ['date', 'price']
                prices['date'] = pd.to_datetime(prices['date']).dt.date
                prices['price'] = pd.to_numeric(prices['price'], errors='coerce')
                prices = prices.dropna()
                
                if len(prices) > 0:
                    result[name] = prices
        except Exception:
            pass
    
    return result


@st.cache_data(ttl=600)
def get_benchmark_roi(_engine):
    """Quick Benchmark (BTC ROI since first snapshot)"""
    session = get_session(_engine)
    try:
        first_date = session.query(Snapshot.date).order_by(Snapshot.date).first()
        if not first_date:
            return None
        first_date = first_date[0]
        
        first_btc = session.query(PriceHistory).filter(
            PriceHistory.symbol == 'BTC',
            PriceHistory.date == first_date
        ).first()
        
        latest_btc = session.query(PriceHistory).filter(
            PriceHistory.symbol == 'BTC'
        ).order_by(desc(PriceHistory.date)).first()
        
        if first_btc and latest_btc and first_btc.price_usd > 0:
            return ((latest_btc.price_usd / first_btc.price_usd) - 1) * 100
        return None
    finally:
        session.close()
