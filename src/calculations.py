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


@st.cache_data(ttl=600, persist="disk")
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


@st.cache_data(ttl=600, persist="disk")
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


@st.cache_data(ttl=600, persist="disk")
def calculate_transfers_summary(_engine: Engine) -> Dict[str, float]:
    """
    计算转账资金流汇总 (SQL Aggregation Optimization)
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        dict: 包含以下键的字典：
            - total_deposits: 总入金
            - total_withdrawals: 总出金
            - net_investment: 净投资（入金 - 出金）
            - net_flow: 净现金流
    """
    from sqlalchemy import func
    
    with session_scope(_engine) as session:
        # 使用 SQL 聚合查询
        total_deposits = session.query(func.sum(Transfer.amount_usd)).filter(
            Transfer.type == 'deposit'
        ).scalar() or 0.0
        
        total_withdrawals = session.query(func.sum(Transfer.amount_usd)).filter(
            Transfer.type == 'withdrawal'
        ).scalar() or 0.0
        
        net_flow = total_deposits - total_withdrawals
        
        return {
            'total_deposits': float(total_deposits),
            'total_withdrawals': float(total_withdrawals),
            'net_investment': float(net_flow),
            'net_flow': float(net_flow)
        }


@st.cache_data(ttl=600, persist="disk")
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


@st.cache_data(ttl=600, persist="disk")
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


@st.cache_data(ttl=600, persist="disk")
def get_net_worth_history(_engine: Engine) -> pd.DataFrame:
    """
    获取净值历史记录 (Bulk Load Optimization)
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        pd.DataFrame: 包含 date 和 net_worth 列的 DataFrame
    """
    from src.database import get_all_snapshots, get_all_prices
    
    # Bulk load snapshots and prices
    snaps_df = get_all_snapshots(_engine)
    prices_df = get_all_prices(_engine)
    
    if snaps_df.empty:
        return pd.DataFrame()
    
    # Standardize column names (to_dict produces lower case keys usually)
    # Ensure they have required columns
    required_snap_cols = ['date', 'symbol', 'quantity']
    required_price_cols = ['date', 'symbol', 'price_usd']
    
    if not all(col in snaps_df.columns for col in required_snap_cols):
        return pd.DataFrame()
        
    # Prepare dataframes for merge_asof
    # Convert dates to datetime64[ns]
    snaps_df['date'] = pd.to_datetime(snaps_df['date'])
    snaps_df = snaps_df.sort_values('date')
    
    if prices_df.empty:
        # If no prices, all values are 0 (or handled gracefully)
        prices_df = pd.DataFrame({'date': [], 'symbol': [], 'price_usd': []})
    else:
        prices_df['date'] = pd.to_datetime(prices_df['date'])
        prices_df = prices_df.sort_values('date')
    
    # Loop through unique symbols present in snapshots to find their prices
    # merge_asof requires sorting by 'on' key. We do this per symbol group effectively.
    
    # Strategy:
    # 1. Get unique symbols from snapshots
    # 2. For each symbol, filter both DFs
    # 3. merge_asof on date
    # 4. Concatenate results
    
    unique_symbols = snaps_df['symbol'].unique()
    merged_frames = []
    
    for symbol in unique_symbols:
        s_df = snaps_df[snaps_df['symbol'] == symbol].copy()
        p_df = prices_df[prices_df['symbol'] == symbol].copy()
        
        if p_df.empty:
            s_df['price_usd'] = 0.0
        else:
            # merge_asof: left frame (snapshots) looks for nearest past date in right frame (prices)
            # Ensure both are sorted by date (should be already, but safety first)
            s_df = s_df.sort_values('date')
            p_df = p_df.sort_values('date')
            
            s_df = pd.merge_asof(
                s_df, 
                p_df[['date', 'price_usd']], 
                on='date', 
                direction='backward'
            )
            s_df['price_usd'] = s_df['price_usd'].fillna(0.0)
        
        # Calculate value
        s_df['value'] = s_df['quantity'] * s_df['price_usd']
        merged_frames.append(s_df)
        
    if not merged_frames:
        return pd.DataFrame()
        
    full_df = pd.concat(merged_frames)
    
    # Aggregation by date
    history = full_df.groupby('date')['value'].sum().reset_index()
    history.columns = ['date', 'net_worth']
    
    # Convert datetime back to date object for consistency with other parts of app
    history['date'] = history['date'].dt.date
    
    return history


@st.cache_data(ttl=3600, persist="disk")
def get_benchmark_history(start_date: date, end_date: date) -> Dict[str, pd.DataFrame]:
    """
    获取基准指数价格历史（使用 yfinance）
    注意：yfinance.download 非线程安全，必须串行调用
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        dict: {指数名称: 价格 DataFrame} 映射
    """
    import yfinance as yf
    
    # S&P500 使用多个候选 ticker，依次尝试
    benchmarks = {
        'S&P500': ['^GSPC', 'SPY'],   # SPY 作为备选（ETF 跟踪标普500）
        'QQQ':    ['QQQ'],
        'BTC':    ['BTC-USD'],
        '沪深300': ['000300.SS'],
        '黄金':    ['GC=F', 'GLD'],    # GLD 作为备选（黄金 ETF）
        # ===== Magnificent 7 个股 =====
        'AAPL':   ['AAPL'],
        'MSFT':   ['MSFT'],
        'GOOGL':  ['GOOGL', 'GOOG'],
        'AMZN':   ['AMZN'],
        'NVDA':   ['NVDA'],
        'META':   ['META'],
        'TSLA':   ['TSLA'],
        # ===== Magnificent 7 组合 ETF =====
        'MAG7 ETF': ['MAGS'],          # Roundhill Magnificent Seven ETF
        # ===== 其他热门基准 =====
        'ETH':      ['ETH-USD'],
        '罗素2000':  ['IWM'],            # iShares Russell 2000 ETF
        '恒生科技':  ['^HSTECH', '3067.HK'],  # 恒生科技指数 / ETF
        '美债20年':  ['TLT'],            # iShares 20+ Year Treasury Bond ETF
        '日经225':   ['^N225'],
    }
    
    result = {}
    
    # 日期格式转换
    start_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else str(start_date)
    end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d') if isinstance(end_date, date) else str(end_date)
    
    for name, tickers in benchmarks.items():
        fetched = False
        for ticker in tickers:
            try:
                data = yf.download(
                    ticker, 
                    start=start_str, 
                    end=end_str,
                    progress=False,
                    auto_adjust=True,
                    timeout=15
                )
                
                if data.empty:
                    print(f"⚠ [Benchmark] {name} ({ticker}): 返回空数据，尝试下一个 ticker")
                    continue
                
                # 安全提取 Close 列，兼容 MultiIndex 和普通 Index
                if isinstance(data.columns, pd.MultiIndex):
                    close_series = data['Close']
                    if isinstance(close_series, pd.DataFrame):
                        close_series = close_series.iloc[:, 0]
                elif 'Close' in data.columns:
                    close_series = data['Close']
                else:
                    print(f"✗ [Benchmark] {name} ({ticker}): 'Close' not found, columns={data.columns.tolist()}")
                    continue
                
                prices = close_series.reset_index()
                prices.columns = ['date', 'price']
                prices['date'] = pd.to_datetime(prices['date']).dt.date
                prices['price'] = pd.to_numeric(prices['price'], errors='coerce')
                prices = prices.dropna()
                
                if len(prices) > 0:
                    result[name] = prices
                    fetched = True
                    if ticker != tickers[0]:
                        print(f"✓ [Benchmark] {name}: 使用备选 ticker {ticker} 成功获取 {len(prices)} 条数据")
                    break
                    
            except Exception as e:
                print(f"✗ [Benchmark] {name} ({ticker}) 获取失败: {e}")
                continue
        
        if not fetched:
            print(f"✗ [Benchmark] {name}: 所有 ticker 均失败")
    
    return result


@st.cache_data(ttl=600, persist="disk")
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
