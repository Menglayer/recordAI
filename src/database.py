"""
Database operations module
"""
import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from src.models import Snapshot, Transfer, PriceHistory


def get_session(engine):
    """Get a database session"""
    Session = sessionmaker(bind=engine)
    return Session()


def save_snapshots_batch(engine, snapshot_date, account_name, snapshot_data):
    """Save batch snapshots"""
    session = get_session(engine)
    
    try:
        # Delete existing snapshots for same date and account
        session.query(Snapshot).filter(
            Snapshot.date == snapshot_date,
            Snapshot.account_name == account_name
        ).delete()
        
        # Add new snapshots
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
        
        session.commit()
        return added
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_transfer(engine, transfer_date, transfer_type, amount_usd, note=None):
    """Save transfer record"""
    session = get_session(engine)
    
    try:
        transfer = Transfer(
            date=transfer_date,
            type=transfer_type,
            amount_usd=amount_usd,
            note=note
        )
        session.add(transfer)
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


@st.cache_data(ttl=60)
def get_recent_snapshots(_engine, limit=10):
    """Get recent snapshots"""
    session = get_session(_engine)
    try:
        snapshots = session.query(Snapshot).order_by(desc(Snapshot.date), desc(Snapshot.id)).limit(limit).all()
        return pd.DataFrame([s.to_dict() for s in snapshots])
    finally:
        session.close()


@st.cache_data(ttl=60)
def get_recent_transfers(_engine, limit=10):
    """Get recent transfers"""
    session = get_session(_engine)
    try:
        transfers = session.query(Transfer).order_by(desc(Transfer.date), desc(Transfer.id)).limit(limit).all()
        return pd.DataFrame([t.to_dict() for t in transfers])
    finally:
        session.close()


@st.cache_data(ttl=60)
def get_unique_accounts(_engine):
    """Get unique account names"""
    session = get_session(_engine)
    try:
        accounts = session.query(Snapshot.account_name).distinct().all()
        return [a[0] for a in accounts]
    finally:
        session.close()


@st.cache_data(ttl=60)
def get_latest_snapshot_date(_engine):
    """Get latest snapshot date"""
    session = get_session(_engine)
    try:
        result = session.query(Snapshot.date).order_by(desc(Snapshot.date)).first()
        return result[0] if result else None
    finally:
        session.close()


@st.cache_data(ttl=300)
def get_price_for_date(_engine, symbol, target_date):
    """Get price for date, use latest if not available"""
    session = get_session(_engine)
    try:
        # First try exact date
        price = session.query(PriceHistory).filter(
            PriceHistory.symbol == symbol,
            PriceHistory.date == target_date
        ).first()
        
        if price:
            return price.price_usd
        
        # Fall back to latest price before target date
        price = session.query(PriceHistory).filter(
            PriceHistory.symbol == symbol,
            PriceHistory.date <= target_date
        ).order_by(desc(PriceHistory.date)).first()
        
        if price:
            return price.price_usd
        
        # Fall back to any latest price
        price = session.query(PriceHistory).filter(
            PriceHistory.symbol == symbol
        ).order_by(desc(PriceHistory.date)).first()
        
        return price.price_usd if price else 0
    finally:
        session.close()


def get_all_snapshots(engine):
    """Get all snapshots"""
    session = get_session(engine)
    try:
        snapshots = session.query(Snapshot).order_by(desc(Snapshot.date)).all()
        return pd.DataFrame([s.to_dict() for s in snapshots])
    finally:
        session.close()


def get_all_transfers(engine):
    """Get all transfers"""
    session = get_session(engine)
    try:
        transfers = session.query(Transfer).order_by(desc(Transfer.date)).all()
        return pd.DataFrame([t.to_dict() for t in transfers])
    finally:
        session.close()


def get_all_prices(engine):
    """Get all prices"""
    session = get_session(engine)
    try:
        prices = session.query(PriceHistory).order_by(desc(PriceHistory.date)).all()
        return pd.DataFrame([p.to_dict() for p in prices])
    finally:
        session.close()


def delete_snapshot(engine, snapshot_id):
    """Delete a snapshot by ID"""
    session = get_session(engine)
    try:
        session.query(Snapshot).filter(Snapshot.id == snapshot_id).delete()
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()


def delete_transfer(engine, transfer_id):
    """Delete a transfer by ID"""
    session = get_session(engine)
    try:
        session.query(Transfer).filter(Transfer.id == transfer_id).delete()
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()


def delete_price(engine, price_id):
    """Delete a price by ID"""
    session = get_session(engine)
    try:
        session.query(PriceHistory).filter(PriceHistory.id == price_id).delete()
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()
