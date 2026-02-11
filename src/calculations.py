"""
Business calculations module
提供资产净值计算、收益率分析等业务逻辑
"""
from typing import Dict, List, Optional, Any
from datetime import date, timedelta

import streamlit as st
import pandas as pd
from sqlalchemy import desc
from sqlalchemy.engine import Engine

from src.models import Snapshot, Transfer, PriceHistory
from src.database import session_scope, get_prices_batch, get_latest_snapshot_date


@st.cache_data(ttl=600)
def calculate_net_worth_for_date(_engine: Engine, target_date: date) -> pd.DataFrame:
    """
    计算指定日期的资产净值
    
    Args:
        _engine: 数据库引擎
        target_date: 目标日期
        
    Returns:
        pd.DataFrame: 包含 account_name, symbol, quantity, price, value 列的 DataFrame
    """
    with session_scope(_engine) as session:
        snapshots = session.query(Snapshot).filter(Snapshot.date == target_date).all()
        
        if not snapshots:
            return pd.DataFrame()
        
        # 批量获取所有需要的价格（优化 N+1 查询）
        symbols = list({s.symbol for s in snapshots})
        prices = get_prices_batch(_engine, symbols, target_date)
        
        # 在内存中计算价值
        data = []
        for s in snapshots:
            price = prices.get(s.symbol, 0)
            value = s.quantity * price
            data.append({
                'account_name': s.account_name,
                'symbol': s.symbol,
                'quantity': s.quantity,
                'price': price,
                'value': value
            })
        
        return pd.DataFrame(data)


@st.cache_data(ttl=600)
def calculate_current_net_worth(_engine: Engine) -> Dict[str, Any]:
    """
    计算当前资产净值
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        dict: 包含以下键的字典：
            - total_net_worth: 总净值
            - latest_date: 最新快照日期
            - by_symbol: 按资产汇总的 DataFrame
            - by_account: 按账户汇总的 DataFrame
            - details: 详细持仓 DataFrame
    """
    latest_date = get_latest_snapshot_date(_engine)
    
    empty_result = {
        'total_net_worth': 0,
        'latest_date': None,
        'by_symbol': pd.DataFrame(),
        'by_account': pd.DataFrame(),
        'details': pd.DataFrame()
    }
    
    if not latest_date:
        return empty_result
    
    details_df = calculate_net_worth_for_date(_engine, latest_date)
    
    if details_df.empty:
        empty_result['latest_date'] = latest_date
        return empty_result
    
    total = details_df['value'].sum()
    by_symbol = details_df.groupby('symbol').agg({
        'quantity': 'sum', 
        'value': 'sum'
    }).reset_index()
    by_account = details_df.groupby('account_name').agg({
        'value': 'sum'
    }).reset_index()
    
    return {
        'total_net_worth': total,
        'latest_date': latest_date,
        'by_symbol': by_symbol,
        'by_account': by_account,
        'details': details_df
    }


@st.cache_data(ttl=600)
def calculate_transfers_summary(_engine: Engine) -> Dict[str, float]:
    """
    计算转账资金流汇总
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        dict: 包含以下键的字典：
            - total_deposits: 总入金
            - total_withdrawals: 总出金
            - net_investment: 净投资（入金 - 出金）
            - net_flow: 净现金流
    """
    with session_scope(_engine) as session:
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


@st.cache_data(ttl=600)
def calculate_pnl(_engine: Engine) -> Dict[str, float]:
    """
    计算盈亏（PnL）
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        dict: 包含以下键的字典：
            - unrealized_pnl: 未实现盈亏
            - roi_percentage: 投资回报率百分比
            - net_worth: 当前净值
            - cost_basis: 成本基础
    """
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
def calculate_time_based_returns(_engine: Engine) -> Dict[str, Any]:
    """
    计算基于时间的收益率和年化收益
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        dict: 包含收益率数据的字典，若数据不足则返回 {'has_data': False}
    """
    with session_scope(_engine) as session:
        # 获取所有快照日期
        dates = session.query(Snapshot.date).distinct().order_by(Snapshot.date).all()
        dates = [d[0] for d in dates]
        
        if len(dates) < 2:
            return {'has_data': False}
        
        start_date = dates[0]
        end_date = dates[-1]
        
        # 计算期初和期末净值
        start_df = calculate_net_worth_for_date(_engine, start_date)
        end_df = calculate_net_worth_for_date(_engine, end_date)
        
        start_net_worth = start_df['value'].sum() if not start_df.empty else 0
        end_net_worth = end_df['value'].sum() if not end_df.empty else 0
        
        if start_net_worth == 0:
            return {'has_data': False}
        
        # 获取期间转账记录
        transfers = session.query(Transfer).filter(
            Transfer.date >= start_date,
            Transfer.date <= end_date
        ).all()
        
        period_deposits = sum(t.amount_usd for t in transfers if t.type == 'deposit')
        period_withdrawals = sum(t.amount_usd for t in transfers if t.type == 'withdrawal')
        net_cash_flow = period_deposits - period_withdrawals
        
        # 时间计算
        total_days = (end_date - start_date).days
        total_hours = total_days * 24
        
        if total_days == 0:
            return {'has_data': False}
        
        # 简单 ROI（扣除现金流影响）
        adjusted_end = end_net_worth - net_cash_flow
        roi = ((adjusted_end / start_net_worth) - 1) * 100
        
        # 年化收益率
        years = total_days / 365
        apr = roi / years if years > 0 else roi
        apy = ((1 + roi / 100) ** (1 / years) - 1) * 100 if years > 0 else roi
        
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


@st.cache_data(ttl=600)
def get_net_worth_history(_engine: Engine) -> pd.DataFrame:
    """
    获取净值历史记录
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        pd.DataFrame: 包含 date 和 net_worth 列的 DataFrame
    """
    with session_scope(_engine) as session:
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


@st.cache_data(ttl=3600)
def get_benchmark_history(start_date: date, end_date: date) -> Dict[str, pd.DataFrame]:
    """
    获取基准指数价格历史（使用 yfinance）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        dict: {指数名称: 价格 DataFrame} 映射
    """
    import yfinance as yf
    
    benchmarks = {
        'S&P500': '^GSPC',
        'QQQ': 'QQQ',
        'BTC': 'BTC-USD',
        '沪深300': '000300.SS'
    }
    
    result = {}
    
    # 日期格式转换
    start_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else str(start_date)
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d') if isinstance(end_date, date) else str(end_date)
    
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def fetch_single_benchmark(name, ticker):
        try:
            data = yf.download(
                ticker, 
                start=start_str, 
                end=end_str,
                progress=False,
                auto_adjust=True
            )
            
            if not data.empty:
                # 处理多层索引列
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                prices = data[['Close']].reset_index()
                prices.columns = ['date', 'price']
                prices['date'] = pd.to_datetime(prices['date']).dt.date
                prices['price'] = pd.to_numeric(prices['price'], errors='coerce')
                prices = prices.dropna()
                
                if len(prices) > 0:
                    return name, prices
        except Exception:
            pass
        return name, None

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_name = {
            executor.submit(fetch_single_benchmark, name, ticker): name 
            for name, ticker in benchmarks.items()
        }
        
        for future in as_completed(future_to_name):
            name, df = future.result()
            if df is not None:
                result[name] = df
    
    return result


@st.cache_data(ttl=600)
def get_benchmark_roi(_engine: Engine) -> Optional[float]:
    """
    计算 BTC 基准收益率（从首次快照至今）
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        Optional[float]: BTC 收益率百分比，若无数据返回 None
    """
    with session_scope(_engine) as session:
        first_date_result = session.query(Snapshot.date).order_by(Snapshot.date).first()
        if not first_date_result:
            return None
        first_date = first_date_result[0]
        
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
