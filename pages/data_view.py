"""
Data view page - View and manage raw data
"""
import streamlit as st
import pandas as pd

from src.models import Snapshot, Transfer, PriceHistory
from src.database import (
    session_scope, get_unique_accounts,
    get_recent_snapshots, get_recent_transfers
)
from src.utils import clear_data_cache
from src import lang as L
from src import styles as S


def show_data_view_page(engine):
    """Data view page"""
    
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="margin: 0;">📋 数据查看</h2>
        <p style="color: #64748B; font-size: 0.85rem; margin-top: 4px;">查看、管理和导出您的数据</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize archived accounts in session state
    if 'archived_accounts' not in st.session_state:
        st.session_state['archived_accounts'] = []
    
    # Account Management Section
    S.section_header("📦", "账户管理")
    
    existing_accounts = get_unique_accounts(engine)
    active_accounts = [a for a in existing_accounts if a not in st.session_state['archived_accounts']]
    archived_accounts = [a for a in existing_accounts if a in st.session_state['archived_accounts']]
    
    # Archive account
    if active_accounts:
        st.caption("⬇️ 选择要隐藏的账户（历史数据保留）")
        hide_col1, hide_col2 = st.columns([3, 1])
        
        with hide_col1:
            account_to_hide = st.selectbox(
                "选择要隐藏的账户",
                options=[""] + active_accounts,
                index=0,
                label_visibility="collapsed",
                placeholder="选择账户...",
                key="hide_account_select"
            )
        
        with hide_col2:
            if account_to_hide and st.button("📦 隐藏", use_container_width=True):
                st.session_state['archived_accounts'].append(account_to_hide)
                clear_data_cache()
                S.toast(f"✅ 已隐藏账户 {account_to_hide}", "success")
                st.rerun()
    
    # Restore archived account
    if archived_accounts:
        st.caption("📦 已隐藏的账户")
        for acc in archived_accounts:
            restore_col1, restore_col2 = st.columns([3, 1])
            with restore_col1:
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: #F8FAFC; border-radius: 8px;">
                    <span>📦</span>
                    <span style="font-weight: 600; color: #64748B;">{acc}</span>
                    {S.badge("已隐藏", "gray")}
                </div>
                """, unsafe_allow_html=True)
            with restore_col2:
                if st.button("🔄 恢复", key=f"restore_{acc}", use_container_width=True):
                    st.session_state['archived_accounts'].remove(acc)
                    clear_data_cache()
                    S.toast(f"✅ 已恢复账户 {acc}", "success")
                    st.rerun()
    
    if not existing_accounts:
        S.empty_state("📭", "暂无账户数据", "请先在数据录入页面添加快照记录")
    
    S.divider()
    
    # Export section
    S.section_header("📥", "数据导出")
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        with session_scope(engine) as session:
            all_snapshots = session.query(Snapshot).order_by(Snapshot.date.desc()).all()
            if all_snapshots:
                snapshot_df = pd.DataFrame([{
                    '日期': s.date,
                    '账户': s.account_name,
                    '币种': s.symbol,
                    '数量': s.quantity
                } for s in all_snapshots])
                csv = snapshot_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 导出快照",
                    csv,
                    "snapshots.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    with export_col2:
        with session_scope(engine) as session:
            all_transfers = session.query(Transfer).order_by(Transfer.date.desc()).all()
            if all_transfers:
                transfer_df = pd.DataFrame([{
                    '日期': t.date,
                    '类型': '入金' if t.type == 'deposit' else '出金',
                    '金额': t.amount_usd,
                    '备注': t.note or ''
                } for t in all_transfers])
                csv = transfer_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "💸 导出转账",
                    csv,
                    "transfers.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    with export_col3:
        with session_scope(engine) as session:
            all_prices = session.query(PriceHistory).order_by(PriceHistory.date.desc()).all()
            if all_prices:
                price_df = pd.DataFrame([{
                    '日期': p.date,
                    '币种': p.symbol,
                    '价格': p.price_usd,
                    '来源': p.source or 'manual'
                } for p in all_prices])
                csv = price_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "💰 导出价格",
                    csv,
                    "prices.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    # 完整备份区域
    S.divider()
    S.section_header("💾", "完整备份")
    st.caption("导出所有数据，可用于灾难恢复")
    
    backup_col1, backup_col2, _ = st.columns([1, 1, 2])
    
    # 生成备份数据
    import json
    from datetime import datetime
    
    with session_scope(engine) as session:
        # 获取所有数据
        all_snapshots = session.query(Snapshot).all()
        all_transfers = session.query(Transfer).all()
        all_prices = session.query(PriceHistory).all()
        
        # 构建 JSON 数据
        backup_data = {
            'export_time': str(datetime.utcnow()),
            'snapshots': [{
                'id': s.id,
                'date': str(s.date),
                'account_name': s.account_name,
                'symbol': s.symbol,
                'quantity': s.quantity,
                'created_at': str(s.created_at) if s.created_at else None
            } for s in all_snapshots],
            'transfers': [{
                'id': t.id,
                'date': str(t.date),
                'type': t.type,
                'amount_usd': t.amount_usd,
                'note': t.note,
                'created_at': str(t.created_at) if t.created_at else None
            } for t in all_transfers],
            'prices': [{
                'id': p.id,
                'date': str(p.date),
                'symbol': p.symbol,
                'price_usd': p.price_usd,
                'source': p.source,
                'created_at': str(p.created_at) if p.created_at else None
            } for p in all_prices],
            'summary': {
                'total_snapshots': len(all_snapshots),
                'total_transfers': len(all_transfers),
                'total_prices': len(all_prices)
            }
        }
        
        # 生成 SQL 恢复脚本
        sql_lines = []
        sql_lines.append("-- MyLedger Backup")
        sql_lines.append(f"-- Exported at: {backup_data['export_time']}")
        sql_lines.append("")
        sql_lines.append("-- Snapshots")
        for s in backup_data['snapshots']:
            sql_lines.append(
                f"INSERT INTO snapshots (date, account_name, symbol, quantity) "
                f"VALUES ('{s['date']}', '{s['account_name']}', '{s['symbol']}', {s['quantity']});"
            )
        sql_lines.append("")
        sql_lines.append("-- Transfers")
        for t in backup_data['transfers']:
            note = (t['note'] or '').replace("'", "''")
            sql_lines.append(
                f"INSERT INTO transfers (date, type, amount_usd, note) "
                f"VALUES ('{t['date']}', '{t['type']}', {t['amount_usd']}, '{note}');"
            )
        sql_lines.append("")
        sql_lines.append("-- Prices")
        for p in backup_data['prices']:
            source = (p['source'] or '').replace("'", "''")
            sql_lines.append(
                f"INSERT INTO price_history (date, symbol, price_usd, source) "
                f"VALUES ('{p['date']}', '{p['symbol']}', {p['price_usd']}, '{source}');"
            )
        
        with backup_col1:
            json_content = json.dumps(backup_data, ensure_ascii=False, indent=2)
            st.download_button(
                "📦 下载 JSON 备份",
                json_content.encode('utf-8'),
                f"myledger_backup_{datetime.now().strftime('%Y%m%d')}.json",
                "application/json",
                use_container_width=True,
                help="完整数据备份，包含所有快照、转账、价格记录"
            )
        
        with backup_col2:
            sql_content = "\n".join(sql_lines)
            st.download_button(
                "🔧 下载 SQL 脚本",
                sql_content.encode('utf-8'),
                f"myledger_restore_{datetime.now().strftime('%Y%m%d')}.sql",
                "text/plain",
                use_container_width=True,
                help="SQL 恢复脚本，可直接在数据库执行"
            )
        
        # 统计信息
        st.markdown(f"""
        <div style="display: flex; gap: 12px; margin-top: 8px;">
            {S.badge(f"📸 快照 {len(all_snapshots)} 条", "blue")}
            {S.badge(f"💸 转账 {len(all_transfers)} 条", "green")}
            {S.badge(f"💰 价格 {len(all_prices)} 条", "orange")}
        </div>
        """, unsafe_allow_html=True)
    
    S.divider()
    
    tab1, tab2, tab3 = st.tabs([L.VIEW_SNAPSHOTS, L.VIEW_TRANSFERS, L.VIEW_PRICES])
    
    with tab1:
        _render_snapshots_tab(engine)
    
    with tab2:
        _render_transfers_tab(engine)
    
    with tab3:
        _render_prices_tab(engine)


def _render_snapshots_tab(engine):
    """Render snapshots tab with delete functionality"""
    st.subheader(L.VIEW_RECENT + " " + L.VIEW_SNAPSHOTS)
    snapshots = get_recent_snapshots(engine, 20)
    
    if not snapshots.empty:
        data = [{
            L.ENTRY_DATE: row['date'],
            L.ENTRY_ACCOUNT: row['account_name'],
            L.ENTRY_SYMBOL: row['symbol'],
            L.ENTRY_QUANTITY: f"{row['quantity']:,.8f}".rstrip('0').rstrip('.')
        } for _, row in snapshots.iterrows()]
        
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        
        # Delete by date
        with st.expander("🗑️ 删除快照记录", expanded=False):
            st.caption("⚠️ 删除操作不可恢复，请谨慎操作")
            
            with session_scope(engine) as session:
                dates = session.query(Snapshot.date).distinct().order_by(Snapshot.date.desc()).limit(30).all()
                date_options = [d[0] for d in dates]
            
            if date_options:
                del_col1, del_col2 = st.columns([2, 1])
                with del_col1:
                    selected_date = st.selectbox(
                        "选择要删除的日期",
                        options=date_options,
                        format_func=lambda d: str(d),
                        key="del_snapshot_date"
                    )
                with del_col2:
                    if st.button("🗑️ 删除该日期全部快照", key="del_snapshot_btn", type="primary"):
                        with session_scope(engine) as session:
                            count = session.query(Snapshot).filter(
                                Snapshot.date == selected_date
                            ).delete()
                            clear_data_cache()
                            S.toast(f"已删除 {selected_date} 的 {count} 条快照记录", "info")
                            st.rerun()
    else:
        S.empty_state("📸", "暂无快照记录", "前往「数据录入」页面添加您的资产快照")


def _render_transfers_tab(engine):
    """Render transfers tab with delete functionality"""
    st.subheader(L.VIEW_RECENT + " " + L.VIEW_TRANSFERS)
    transfers = get_recent_transfers(engine, 20)
    
    if not transfers.empty:
        data = [{
            L.ENTRY_DATE: row['date'],
            L.TRANSFER_TYPE: L.TRANSFER_DEPOSIT if row['type'] == "deposit" else L.TRANSFER_WITHDRAWAL,
            L.TRANSFER_AMOUNT: f"${row['amount_usd']:,.2f}",
            L.TRANSFER_NOTE: row['note'] or ''
        } for _, row in transfers.iterrows()]
        
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        
        # Delete single transfer
        with st.expander("🗑️ 删除转账记录", expanded=False):
            st.caption("⚠️ 删除操作不可恢复，请谨慎操作")
            
            with session_scope(engine) as session:
                recent_transfers = session.query(Transfer).order_by(Transfer.date.desc()).limit(20).all()
                transfer_options = {
                    f"{t.date} | {'入金' if t.type == 'deposit' else '出金'} ${t.amount_usd:,.2f} {t.note or ''}": t.id
                    for t in recent_transfers
                }
            
            if transfer_options:
                del_col1, del_col2 = st.columns([3, 1])
                with del_col1:
                    selected_transfer = st.selectbox(
                        "选择要删除的记录",
                        options=list(transfer_options.keys()),
                        key="del_transfer_select"
                    )
                with del_col2:
                    if st.button("🗑️ 删除", key="del_transfer_btn", type="primary"):
                        transfer_id = transfer_options[selected_transfer]
                        with session_scope(engine) as session:
                            session.query(Transfer).filter(Transfer.id == transfer_id).delete()
                            clear_data_cache()
                            S.toast("已删除转账记录", "info")
                            st.rerun()
    else:
        S.empty_state("💸", "暂无转账记录", "前往「数据录入」页面记录入金/出金")


def _render_prices_tab(engine):
    """Render prices tab with delete functionality"""
    st.subheader(L.VIEW_RECENT + " " + L.VIEW_PRICES)
    with session_scope(engine) as session:
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
            
            # Delete prices by date
            with st.expander("🗑️ 删除价格记录", expanded=False):
                st.caption("⚠️ 删除操作不可恢复，请谨慎操作")
                
                dates = session.query(PriceHistory.date).distinct().order_by(PriceHistory.date.desc()).limit(30).all()
                date_options = [d[0] for d in dates]
                
                if date_options:
                    del_col1, del_col2 = st.columns([2, 1])
                    with del_col1:
                        selected_date = st.selectbox(
                            "选择要删除的日期",
                            options=date_options,
                            format_func=lambda d: str(d),
                            key="del_price_date"
                        )
                    with del_col2:
                        if st.button("🗑️ 删除该日期全部价格", key="del_price_btn", type="primary"):
                            count = session.query(PriceHistory).filter(
                                PriceHistory.date == selected_date
                            ).delete()
                            clear_data_cache()
                            S.toast(f"已删除 {selected_date} 的 {count} 条价格记录", "info")
                            st.rerun()
        else:
            S.empty_state("💰", "暂无价格记录", "前往「价格更新」页面获取资产价格")
