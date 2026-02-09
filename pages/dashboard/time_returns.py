"""
Dashboard Time Returns Section
时间收益率分析组件
"""
from typing import Callable, Dict, Any
import streamlit as st
from src import styles as S
from src import lang as L


def render_time_returns_section(
    time_returns: Dict[str, Any],
    format_val: Callable,
    fx_rate: float,
    cur_sym: str,
    privacy_on: bool
) -> None:
    """
    渲染时间维度收益率分析区块
    
    Args:
        time_returns: 时间收益率数据
        format_val: 格式化函数
        fx_rate: 汇率
        cur_sym: 货币符号
        privacy_on: 隐私模式开关
    """
    if not time_returns.get('has_data', False):
        return
    
    st.markdown("---")
    st.subheader(L.TIME_RETURNS)
    
    # 隐私模式辅助函数
    def mask(val):
        return "••••••" if privacy_on else val
    
    # 第一行：时间周期、净值变化、现金流
    col_time1, col_time2, col_time3 = st.columns(3)
    
    with col_time1:
        st.markdown(f"""
        <div class="u-card" style="padding: 20px;">
            <div class="m-label">{L.TIME_PERIOD}</div>
            <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                <div><span style="color: var(--falcon-muted);">{L.TIME_START}:</span> <strong>{time_returns['start_date']}</strong></div>
                <div><span style="color: var(--falcon-muted);">{L.TIME_END}:</span> <strong>{time_returns['end_date']}</strong></div>
                <div><span style="color: var(--falcon-muted);">{L.TIME_DAYS}:</span> <strong>{time_returns['days']:.1f}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_time2:
        start_val = mask(format_val(time_returns['start_net_worth'], fx_rate, cur_sym, privacy_on))
        end_val = mask(format_val(time_returns['end_net_worth'], fx_rate, cur_sym, privacy_on))
        change_val = mask(format_val(time_returns['end_net_worth'] - time_returns['start_net_worth'], fx_rate, cur_sym, privacy_on))
        
        st.markdown(f"""
        <div class="u-card" style="padding: 20px;">
            <div class="m-label">{L.TIME_NW_CHANGE}</div>
            <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                <div><span style="color: var(--falcon-muted);">{L.TIME_START}:</span> <strong>{start_val}</strong></div>
                <div><span style="color: var(--falcon-muted);">{L.TIME_END}:</span> <strong>{end_val}</strong></div>
                <div><span style="color: var(--falcon-muted);">{L.TIME_CHANGE}:</span> <strong>{change_val}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_time3:
        deposits = mask(f"{cur_sym}{time_returns.get('period_deposits', 0) * fx_rate:,.2f}")
        withdrawals = mask(f"{cur_sym}{time_returns.get('period_withdrawals', 0) * fx_rate:,.2f}")
        net_flow = mask(f"{cur_sym}{time_returns['net_cash_flow'] * fx_rate:,.2f}")
        
        st.markdown(f"""
        <div class="u-card" style="padding: 20px;">
            <div class="m-label">{L.TIME_CASH_FLOW}</div>
            <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.8;">
                <div><span style="color: var(--falcon-muted);">{L.TIME_DEPOSITS}:</span> <strong style="color: #10B981;">{deposits}</strong></div>
                <div><span style="color: var(--falcon-muted);">{L.TIME_WITHDRAWALS}:</span> <strong style="color: #EF4444;">{withdrawals}</strong></div>
                <div><span style="color: var(--falcon-muted);">{L.TIME_NET}:</span> <strong>{net_flow}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 第二行：ROI、APR、APY
    col_apy1, col_apy2, col_apy3 = st.columns(3)
    
    with col_apy1:
        roi_val = f"{time_returns['roi']:.2f}%"
        S.metric_card(
            label=L.TIME_PERIOD_ROI,
            value=roi_val,
            delta=f"{time_returns['days']:.1f} 天",
            delta_up=time_returns['roi'] >= 0
        )
    
    with col_apy2:
        apr_val = f"{time_returns['apr']:,.2f}%"
        S.metric_card(
            label="年化收益 (APR)",
            value=apr_val,
            delta="简单年化",
            delta_up=time_returns['apr'] >= 0
        )
    
    with col_apy3:
        apy_val = f"{time_returns['apy']:,.2f}%"
        S.metric_card(
            label="复利年化 (APY)",
            value=apy_val,
            delta="复利计算" if abs(time_returns['apy']) < 1000 else L.TIME_HIGH_VOL,
            delta_up=time_returns['apy'] >= 0
        )
