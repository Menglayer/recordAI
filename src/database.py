"""
Database operations module
提供数据库连接、会话管理和 CRUD 操作
"""
from contextlib import contextmanager
from typing import Optional, List, Generator, Any

import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.models import Snapshot, Transfer, PriceHistory


@contextmanager
def session_scope(engine: Engine) -> Generator[Session, None, None]:
    """
    数据库会话上下文管理器
    自动处理 commit/rollback/close
    
    Args:
        engine: SQLAlchemy 数据库引擎
        
    Yields:
        Session: 数据库会话对象
        
    Example:
        with session_scope(engine) as session:
            snapshots = session.query(Snapshot).all()
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def get_session(engine: Engine) -> Session:
    """
    获取数据库会话（向后兼容）
    建议使用 session_scope 上下文管理器替代
    
    Args:
        engine: SQLAlchemy 数据库引擎
        
    Returns:
        Session: 数据库会话对象
    """
    SessionFactory = sessionmaker(bind=engine)
    return SessionFactory()


def save_snapshots_batch(
    engine: Engine, 
    snapshot_date: date, 
    account_name: str, 
    snapshot_data: pd.DataFrame
) -> int:
    """
    批量保存快照记录
    
    Args:
        engine: 数据库引擎
        snapshot_date: 快照日期
        account_name: 账户名称
        snapshot_data: 包含 Symbol 和 Quantity 列的 DataFrame
        
    Returns:
        int: 成功添加的记录数
    """
    with session_scope(engine) as session:
        # 删除同日期同账户的旧记录
        session.query(Snapshot).filter(
            Snapshot.date == snapshot_date,
            Snapshot.account_name == account_name
        ).delete()
        
        # 添加新记录
        added = 0
        for _, row in snapshot_data.iterrows():
            symbol = str(row['Symbol']).strip().upper()
            quantity = float(row['Quantity'])
            
            if not symbol or symbol == '' or quantity < 0:
                continue
            
            snapshot = Snapshot(
                date=snapshot_date,
                account_name=account_name,
                symbol=symbol,
                quantity=quantity
            )
            session.add(snapshot)
            added += 1
        
        return added


def save_transfer(
    engine: Engine, 
    transfer_date: date, 
    transfer_type: str, 
    amount_usd: float, 
    note: Optional[str] = None
) -> bool:
    """
    保存转账记录
    
    Args:
        engine: 数据库引擎
        transfer_date: 转账日期
        transfer_type: 类型 ('deposit' 或 'withdrawal')
        amount_usd: 金额（美元）
        note: 可选备注
        
    Returns:
        bool: 是否保存成功
    """
    with session_scope(engine) as session:
        transfer = Transfer(
            date=transfer_date,
            type=transfer_type,
            amount_usd=amount_usd,
            note=note
        )
        session.add(transfer)
        return True


@st.cache_data(ttl=60)
def get_recent_snapshots(_engine: Engine, limit: int = 10) -> pd.DataFrame:
    """
    获取最近的快照记录
    
    Args:
        _engine: 数据库引擎（下划线前缀避免 Streamlit 缓存警告）
        limit: 返回记录数限制
        
    Returns:
        pd.DataFrame: 快照记录 DataFrame
    """
    with session_scope(_engine) as session:
        snapshots = session.query(Snapshot).order_by(
            desc(Snapshot.date), desc(Snapshot.id)
        ).limit(limit).all()
        return pd.DataFrame([s.to_dict() for s in snapshots])


@st.cache_data(ttl=60)
def get_recent_transfers(_engine: Engine, limit: int = 10) -> pd.DataFrame:
    """
    获取最近的转账记录
    
    Args:
        _engine: 数据库引擎
        limit: 返回记录数限制
        
    Returns:
        pd.DataFrame: 转账记录 DataFrame
    """
    with session_scope(_engine) as session:
        transfers = session.query(Transfer).order_by(
            desc(Transfer.date), desc(Transfer.id)
        ).limit(limit).all()
        return pd.DataFrame([t.to_dict() for t in transfers])


@st.cache_data(ttl=60)
def get_unique_accounts(_engine: Engine) -> List[str]:
    """
    获取唯一的账户名列表
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        List[str]: 账户名列表
    """
    with session_scope(_engine) as session:
        accounts = session.query(Snapshot.account_name).distinct().all()
        return [a[0] for a in accounts]


@st.cache_data(ttl=60)
def get_latest_snapshot_date(_engine: Engine) -> Optional[date]:
    """
    获取最新快照日期
    
    Args:
        _engine: 数据库引擎
        
    Returns:
        Optional[date]: 最新快照日期，无数据时返回 None
    """
    with session_scope(_engine) as session:
        result = session.query(Snapshot.date).order_by(desc(Snapshot.date)).first()
        return result[0] if result else None


@st.cache_data(ttl=300)
def get_price_for_date(_engine: Engine, symbol: str, target_date: date) -> float:
    """
    获取指定日期的资产价格
    优先使用精确日期，其次使用最近的历史价格
    
    Args:
        _engine: 数据库引擎
        symbol: 资产符号（如 BTC, ETH）
        target_date: 目标日期
        
    Returns:
        float: 资产价格（USD），未找到返回 0
    """
    with session_scope(_engine) as session:
        # 1. 尝试精确日期
        price = session.query(PriceHistory).filter(
            PriceHistory.symbol == symbol,
            PriceHistory.date == target_date
        ).first()
        
        if price:
            return price.price_usd
        
        # 2. 回退到目标日期之前的最新价格
        price = session.query(PriceHistory).filter(
            PriceHistory.symbol == symbol,
            PriceHistory.date <= target_date
        ).order_by(desc(PriceHistory.date)).first()
        
        if price:
            return price.price_usd
        
        # 3. 回退到任意最新价格
        price = session.query(PriceHistory).filter(
            PriceHistory.symbol == symbol
        ).order_by(desc(PriceHistory.date)).first()
        
        return price.price_usd if price else 0


@st.cache_data(ttl=300)
def get_prices_batch(_engine: Engine, symbols: List[str], target_date: date) -> dict:
    """
    批量获取多个资产的价格（解决 N+1 查询问题）
    
    Args:
        _engine: 数据库引擎
        symbols: 资产符号列表
        target_date: 目标日期
        
    Returns:
        dict: {symbol: price} 映射
    """
    if not symbols:
        return {}
    
    with session_scope(_engine) as session:
        # 获取所有符号在目标日期或之前的价格
        from sqlalchemy import func
        
        # 子查询：每个符号在 target_date 之前的最新日期
        subquery = session.query(
            PriceHistory.symbol,
            func.max(PriceHistory.date).label('max_date')
        ).filter(
            PriceHistory.symbol.in_(symbols),
            PriceHistory.date <= target_date
        ).group_by(PriceHistory.symbol).subquery()
        
        # 主查询：获取对应的价格
        prices = session.query(PriceHistory).join(
            subquery,
            (PriceHistory.symbol == subquery.c.symbol) & 
            (PriceHistory.date == subquery.c.max_date)
        ).all()
        
        result = {p.symbol: p.price_usd for p in prices}
        
        # 对于没有找到价格的符号，设为 0
        for sym in symbols:
            if sym not in result:
                result[sym] = 0
        
        return result


def get_all_snapshots(engine: Engine) -> pd.DataFrame:
    """获取所有快照记录"""
    with session_scope(engine) as session:
        snapshots = session.query(Snapshot).order_by(desc(Snapshot.date)).all()
        return pd.DataFrame([s.to_dict() for s in snapshots])


def get_all_transfers(engine: Engine) -> pd.DataFrame:
    """获取所有转账记录"""
    with session_scope(engine) as session:
        transfers = session.query(Transfer).order_by(desc(Transfer.date)).all()
        return pd.DataFrame([t.to_dict() for t in transfers])


def get_all_prices(engine: Engine) -> pd.DataFrame:
    """获取所有价格记录"""
    with session_scope(engine) as session:
        prices = session.query(PriceHistory).order_by(desc(PriceHistory.date)).all()
        return pd.DataFrame([p.to_dict() for p in prices])


def delete_snapshot(engine: Engine, snapshot_id: int) -> bool:
    """
    删除快照记录
    
    Args:
        engine: 数据库引擎
        snapshot_id: 快照 ID
        
    Returns:
        bool: 是否删除成功
    """
    try:
        with session_scope(engine) as session:
            session.query(Snapshot).filter(Snapshot.id == snapshot_id).delete()
            return True
    except SQLAlchemyError:
        return False


def delete_transfer(engine: Engine, transfer_id: int) -> bool:
    """
    删除转账记录
    
    Args:
        engine: 数据库引擎
        transfer_id: 转账 ID
        
    Returns:
        bool: 是否删除成功
    """
    try:
        with session_scope(engine) as session:
            session.query(Transfer).filter(Transfer.id == transfer_id).delete()
            return True
    except SQLAlchemyError:
        return False


def delete_price(engine: Engine, price_id: int) -> bool:
    """
    删除价格记录
    
    Args:
        engine: 数据库引擎
        price_id: 价格 ID
        
    Returns:
        bool: 是否删除成功
    """
    try:
        with session_scope(engine) as session:
            session.query(PriceHistory).filter(PriceHistory.id == price_id).delete()
            return True
    except SQLAlchemyError:
        return False
