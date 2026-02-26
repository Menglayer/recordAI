"""
Dashboard Holdings Table Component
持仓明细表格组件（含占比可视化）
"""
from typing import Dict, Any
import streamlit as st
import pandas as pd
from src import lang as L
from src import styles as S


def render_holdings_table(
    net_worth_data: Dict[str, Any],
    fx_rate: float,
    cur_sym: str
) -> None:
    """
    渲染持仓明细表格（含占比百分比）
    
    Args:
        net_worth_data: 净值数据
        fx_rate: 汇率
        cur_sym: 货币符号
    """
    # Section header is rendered by main.py's section divider
    
    if net_worth_data['details'].empty:
        S.empty_state("📦", L.HOLDINGS_NO_DATA, "请先在数据录入页面添加快照")
        return
    
    details = net_worth_data['details'].copy()
    total_value = details['value'].sum()
    
    # 添加占比列
    details['pct'] = (details['value'] / total_value * 100) if total_value > 0 else 0
    
    # 按价值降序排列
    details = details.sort_values('value', ascending=False)
    
    # 格式化显示
    display_data = []
    for _, row in details.iterrows():
        qty_str = f"{row['quantity']:,.8f}".rstrip('0').rstrip('.')
        price_str = f"{cur_sym}{row['price'] * fx_rate:,.2f}"
        value_str = f"{cur_sym}{row['value'] * fx_rate:,.2f}"
        pct_val = row['pct']
        
        display_data.append({
            L.HOLDINGS_ACCOUNT: row['account_name'],
            L.HOLDINGS_ASSET: row['symbol'],
            L.HOLDINGS_QTY: qty_str,
            L.HOLDINGS_PRICE: price_str,
            L.HOLDINGS_VALUE: value_str,
            '占比': f"{pct_val:.1f}%"
        })
    
    df = pd.DataFrame(display_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            '占比': st.column_config.ProgressColumn(
                '占比',
                help='该资产占总净值的百分比',
                format='%.1f%%',
                min_value=0,
                max_value=100,
            )
        }
    )
    
    # 小额资产提示
    small_count = len(details[details['value'] < 10])
    if small_count > 0:
        st.caption(f"💡 已隐藏 {small_count} 个小额资产（< $10）")
