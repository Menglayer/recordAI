"""
Price update page - Auto fetch and manual price entry
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from sqlalchemy import and_

from src.models import Snapshot, PriceHistory
from src.database import session_scope
from src import price_service
from src.utils import clear_data_cache
from src import lang as L


def show_price_page(engine):
    """Price update page"""
    
    st.markdown("---")
    st.header(L.PRICE_TITLE)
    
    tab1, tab2 = st.tabs([L.PRICE_AUTO, L.PRICE_MANUAL])
    
    with tab1:
        st.subheader(L.PRICE_AUTO)
        
        with session_scope(engine) as session:
            snapshots = session.query(Snapshot.symbol).distinct().order_by(Snapshot.symbol).all()
            symbols_from_snapshots = [s[0] for s in snapshots]
        
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
                            clear_data_cache()
                            st.success(L.PRICE_UPDATED_N.format(count))
                            st.balloons()
                            
                            with session_scope(engine) as session:
                                prices = session.query(PriceHistory).filter(
                                    PriceHistory.date == date.today()
                                ).all()
                                
                                if prices:
                                    price_data = [{
                                        L.PRICE_SYMBOL: p.symbol,
                                        L.PRICE_PRICE: f"${p.price_usd:,.4f}",
                                        L.PRICE_SOURCE: p.source or 'manual'
                                    } for p in prices]
                                    
                                    st.dataframe(pd.DataFrame(price_data), use_container_width=True, hide_index=True)
                            
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
                    try:
                        with session_scope(engine) as session:
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
                        
                        clear_data_cache()
                        st.success(L.PRICE_SAVED.format(symbol, price_usd))
                        
                    except Exception as e:
                        st.error(f"{L.PRICE_SAVE_FAILED}: {e}")

