"""
Data entry page - Snapshot and transfer entry
"""
import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import and_

from src.models import Snapshot, PriceHistory
from src.database import (
    session_scope, save_snapshots_batch, save_transfer, get_unique_accounts, save_journal
)
from src.price_service import update_price_history_db
from src.calculations import calculate_current_net_worth
from src.utils import clear_data_cache
from src import lang as L
from src import styles as S


def _btc_price_exists(engine, target_date):
    """Check if BTC price already exists in DB for the given date"""
    with session_scope(engine) as session:
        existing = session.query(PriceHistory).filter(
            and_(
                PriceHistory.symbol == 'BTC',
                PriceHistory.date == target_date
            )
        ).first()
        return existing is not None


def show_data_entry_page(engine):
    """Data entry page"""
    
    S.page_header("✏️", "数据录入", "记录快照、转账与复盘日记")
    
    tab1, tab2, tab3 = st.tabs([L.ENTRY_SNAPSHOT, L.TRANSFER_TITLE, L.JOURNAL_TITLE])
    
    with tab1:
        # Display success/error message from previous save (survives st.rerun)
        if '_entry_msg' in st.session_state:
            msg_data = st.session_state.pop('_entry_msg')
            if msg_data['type'] == 'success':
                st.success(msg_data['text'], icon="✅")
            elif msg_data['type'] == 'error':
                st.error(msg_data['text'], icon="❌")
        
        st.subheader(L.ENTRY_SNAPSHOT)
        
        col1, col2 = st.columns([1.5, 2])
        
        with col1:
            S.sub_label("⚙️", L.ENTRY_SETTINGS)
            
            snapshot_date = st.date_input(
                L.ENTRY_DATE,
                value=date.today(),
                max_value=date.today(),
                help=L.ENTRY_SNAPSHOT_DATE
            )
            
            existing_accounts = get_unique_accounts(engine)
            
            # Get account balances for sorting and display
            net_worth_data = calculate_current_net_worth(engine)
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
                        with session_scope(engine) as session:
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
            S.sub_label("📊", L.ENTRY_HOLDINGS)
            
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
            ].copy()
            valid_rows['Symbol'] = valid_rows['Symbol'].astype(str).str.strip().str.upper()
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
                ].copy()
                valid_rows['Symbol'] = valid_rows['Symbol'].astype(str).str.strip().str.upper()
                
                if len(valid_rows) == 0:
                    st.warning(L.ENTRY_NO_VALID)
                else:
                    try:
                        with st.spinner("正在保存快照..."):
                            # 1. Save current account's snapshot
                            count = save_snapshots_batch(engine, snapshot_date, account_name, valid_rows)
                            
                            # 2. Auto carry-forward other accounts from previous date
                            carried_count = 0
                            with session_scope(engine) as session:
                                # Find accounts that exist on previous dates but not on current date
                                prev_date = session.query(Snapshot.date).filter(
                                    Snapshot.date < snapshot_date
                                ).order_by(Snapshot.date.desc()).first()
                                
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
                                    clear_data_cache()
                            
                            # Only fetch BTC price if not already in DB for this date
                            if not _btc_price_exists(engine, snapshot_date):
                                try:
                                    update_price_history_db(['BTC'], engine=engine, target_date=snapshot_date)
                                except Exception:
                                    pass
                        
                        # Store success message in session_state so it survives st.rerun()
                        msg = L.ENTRY_SAVED_N.format(count)
                        if carried_count > 0:
                            msg += f" (自动继承其他账户 {carried_count} 条)"
                        st.session_state['_entry_msg'] = {'type': 'success', 'text': f"✅ {msg}"}
                        
                        st.session_state.snapshot_data = pd.DataFrame({'Symbol': [''], 'Quantity': [0.0]})
                        clear_data_cache()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"{L.ENTRY_SAVE_FAILED}: {e}")
    
    with tab2:
        st.subheader(L.TRANSFER_TITLE)
        
        with st.form("transfer_form", clear_on_submit=True):
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
                        save_transfer(engine, transfer_date, transfer_type, amount_usd, note)
                        type_str = L.TRANSFER_DEPOSIT if transfer_type == "deposit" else L.TRANSFER_WITHDRAWAL
                        clear_data_cache()
                        st.success(f"✅ {L.TRANSFER_SAVED.format(type_str, amount_usd)}", icon="✅")
                    except Exception as e:
                        st.error(f"{L.ENTRY_SAVE_FAILED}: {e}")

    with tab3:
        st.subheader("📝 投资复盘")
        
        with st.form("journal_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                j_date = st.date_input("复盘日期", value=date.today())
            with col2:
                j_tags = st.text_input(L.JOURNAL_TAGS, placeholder=L.JOURNAL_TAGS_HINT)
            
            j_content = st.text_area(
                L.JOURNAL_CONTENT, 
                height=250, 
                placeholder=L.JOURNAL_PLACEHOLDER,
                label_visibility="collapsed"
            )
            
            if st.form_submit_button(L.JOURNAL_SAVE, type="primary", use_container_width=True):
                if not j_content or not j_content.strip():
                     st.warning("日记内容不能为空")
                else:
                     try:
                         save_journal(engine, j_date, j_content, j_tags)
                         clear_data_cache()
                         st.success("✅ 日记已保存！", icon="✅")
                     except Exception as e:
                         st.error(f"保存失败: {e}")
