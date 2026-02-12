"""
Utility functions and helpers
"""
import streamlit as st
from src import price_service
from src.config import (
    CURRENCY_SYMBOLS, CACHE_TTL_LONG, CACHE_TTL_MEDIUM,
    DEFAULT_BTC_PRICE_FALLBACK
)


@st.cache_data(ttl=CACHE_TTL_LONG)
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


# Re-export from styles for backward compatibility
from src.styles import MODERN_COLORS  # noqa: F401


@st.cache_data(ttl=CACHE_TTL_MEDIUM)
def get_realtime_btc_price():
    """
    实时获取BTC价格（带缓存）
    复用 PriceService，不再单独创建 ccxt 实例
    
    Returns:
        float: BTC价格（USD）
    """
    # 1. 尝试通过 PriceService 获取实时价格
    try:
        service = price_service.PriceService()
        price = service.fetch_price('BTC')
        if price and price > 0:
            return price
    except Exception as e:
        print(f"⚠️ PriceService 获取BTC价格失败: {e}")
    
    # 2. Fallback: 尝试从数据库获取最新价格
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
    except Exception as e:
        print(f"⚠️ 数据库获取BTC价格失败: {e}")
    
    # 3. 最终 fallback
    return DEFAULT_BTC_PRICE_FALLBACK
