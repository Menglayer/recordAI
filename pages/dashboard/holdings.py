"""
Dashboard Holdings Table Component
持仓明细表格组件
"""
from typing import Dict, Any
import streamlit as st
from src import lang as L


def render_holdings_table(
    net_worth_data: Dict[str, Any],
    fx_rate: float,
    cur_sym: str
) -> None:
    """
    渲染持仓明细表格
    
    Args:
        net_worth_data: 净值数据
        fx_rate: 汇率
        cur_sym: 货币符号
    """
    st.subheader(L.HOLDINGS_DETAIL)
    
    if net_worth_data['details'].empty:
        st.info(L.HOLDINGS_NO_DATA)
        return
    
    details_display = net_worth_data['details'].copy()
    
    # 格式化数量（去除末尾零）
    details_display['quantity'] = details_display['quantity'].apply(
        lambda x: f"{x:,.8f}".rstrip('0').rstrip('.')
    )
    
    # 格式化价格和价值
    details_display['price'] = details_display['price'].apply(
        lambda x: f"{cur_sym}{x * fx_rate:,.2f}"
    )
    details_display['value'] = details_display['value'].apply(
        lambda x: f"{cur_sym}{x * fx_rate:,.2f}"
    )
    
    # 选择并重命名列
    details_display = details_display[['account_name', 'symbol', 'quantity', 'price', 'value']]
    details_display.columns = [
        L.HOLDINGS_ACCOUNT, 
        L.HOLDINGS_ASSET, 
        L.HOLDINGS_QTY, 
        L.HOLDINGS_PRICE, 
        L.HOLDINGS_VALUE
    ]
    
    st.dataframe(details_display, use_container_width=True, hide_index=True)
