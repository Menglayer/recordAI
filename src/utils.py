"""
Utility functions and helpers
"""
import streamlit as st
from src import price_service
from src.config import (
    CURRENCY_SYMBOLS, CACHE_TTL_LONG, CACHE_TTL_MEDIUM,
    DEFAULT_BTC_PRICE_FALLBACK
)


@st.cache_data(ttl=CACHE_TTL_LONG, persist="disk")
def get_fx_rate(to_currency):
    """Get exchange rate from USD to target currency"""
    if to_currency == "USD":
        return 1.0, "$"
    
    symbol = CURRENCY_SYMBOLS.get(to_currency, to_currency + " ")
    
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
        get_unique_accounts, get_latest_snapshot_date, 
        get_price_for_date, get_prices_batch, get_journals
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
    get_prices_batch.clear()
    get_journals.clear()
    
    # Clear calculation caches
    calculate_current_net_worth.clear()
    calculate_transfers_summary.clear()
    calculate_pnl.clear()
    calculate_time_based_returns.clear()
    get_net_worth_history.clear()
    calculate_net_worth_for_date.clear()
    get_benchmark_roi.clear()
    
    # Clear sidebar-related caches (BTC price, FX rate)
    get_realtime_btc_price.clear()
    get_btc_price_db_only.clear()
    get_fx_rate.clear()


# Re-export from styles for backward compatibility
from src.styles import MODERN_COLORS  # noqa: F401


@st.cache_data(ttl=CACHE_TTL_LONG, persist="disk")
def get_btc_price_db_only():
    """
    仅从数据库获取BTC价格（极快，不调API）
    用于非Dashboard页面的侧边栏显示
    
    Returns:
        float: BTC价格（USD），数据库无数据时返回 fallback
    """
    try:
        from src.models import PriceHistory, get_engine
        from src.database import session_scope
        from sqlalchemy import desc
        import os
        
        db_url = os.getenv("DB_URL") or 'local_ledger.db'
        engine = get_engine(db_url)
        
        with session_scope(engine) as session:
            btc_record = session.query(PriceHistory).filter(
                PriceHistory.symbol == 'BTC'
            ).order_by(desc(PriceHistory.date)).first()
            
            if btc_record and btc_record.price_usd > 0:
                return btc_record.price_usd
    except Exception:
        pass
    
    return DEFAULT_BTC_PRICE_FALLBACK


@st.cache_data(ttl=CACHE_TTL_MEDIUM, persist="disk")
def get_realtime_btc_price():
    """
    获取BTC价格（带缓存）
    优先从数据库获取（极快），API作为后备
    
    Returns:
        float: BTC价格（USD）
    """
    # 1. 优先从数据库获取最新价格（极快，不会阻塞）
    try:
        from src.models import PriceHistory, get_engine
        from src.database import session_scope
        from sqlalchemy import desc
        import os
        
        db_url = os.getenv("DB_URL") or 'local_ledger.db'
        engine = get_engine(db_url)
        
        with session_scope(engine) as session:
            btc_record = session.query(PriceHistory).filter(
                PriceHistory.symbol == 'BTC'
            ).order_by(desc(PriceHistory.date)).first()
            
            if btc_record and btc_record.price_usd > 0:
                print(f"✓ [DB Cache] BTC: ${btc_record.price_usd:,.2f}")
                return btc_record.price_usd
    except Exception as e:
        print(f"⚠️ 数据库获取BTC价格失败: {e}")
    
    # 2. 数据库无数据时，尝试API（减少重试，设置超时）
    try:
        service = price_service.PriceService(retry_count=1, retry_delay=1)
        # 设置较短的超时时间，避免卡住
        if hasattr(service, 'binance'):
            service.binance.timeout = 5000  # 5秒超时
        price = service.fetch_price('BTC')
        if price and price > 0:
            return price
    except Exception as e:
        print(f"⚠️ PriceService 获取BTC价格失败: {e}")
    
    # 3. 最终 fallback
    return DEFAULT_BTC_PRICE_FALLBACK
