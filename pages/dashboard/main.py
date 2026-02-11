"""
Dashboard Main Entry Point
Dashboard 主入口，整合所有组件
"""
from datetime import date, timedelta

import streamlit as st
import pandas as pd

from src import lang as L
from src.utils import get_realtime_btc_price, format_val
import src.calculations as calculations

from pages.dashboard.metrics import (
    render_net_worth_card,
    render_goal_progress,
    render_summary_metrics
)
from pages.dashboard.time_returns import render_time_returns_section
from pages.dashboard.charts import (
    render_asset_charts,
    render_history_chart,
    render_monthly_heatmap
)
from pages.dashboard.holdings import render_holdings_table
from pages.dashboard.journal import render_journal_section


def show_dashboard(
    engine,
    privacy_on: bool = False,
    fx_rate: float = 1.0,
    cur_sym: str = "$",
) -> None:
    """
    Dashboard 主页面
    
    Args:
        engine: 数据库引擎
        privacy_on: 隐私模式开关
        fx_rate: 汇率
        cur_sym: 货币符号
    """
    st.markdown("---")
    
    # ========== 数据加载 ==========
    with st.spinner("📊 正在加载数据..."):
        net_worth_data = calculations.calculate_current_net_worth(engine)
        transfers_data = calculations.calculate_transfers_summary(engine)
        pnl_data = calculations.calculate_pnl(engine)
        time_returns = calculations.calculate_time_based_returns(engine)
        benchmark_roi = calculations.get_benchmark_roi(engine)
    
    # ========== 数据过滤 ==========
    archived = st.session_state.get('archived_accounts', [])
    if not net_worth_data['details'].empty:
        filtered_details = net_worth_data['details'].copy()
        
        # 过滤归档账户
        if archived:
            filtered_details = filtered_details[~filtered_details['account_name'].isin(archived)]
        
        # 过滤小额账户（仅用于显示）
        total_net_worth = filtered_details['value'].sum() if not filtered_details.empty else 0
        display_details = filtered_details[filtered_details['value'] >= 10]
        
        # 重新计算显示数据
        net_worth_data = {
            'latest_date': net_worth_data['latest_date'],
            'total_net_worth': total_net_worth,
            'details': display_details,
            'by_symbol': display_details.groupby('symbol').agg({'quantity': 'sum', 'value': 'sum'}).reset_index() if not display_details.empty else pd.DataFrame(),
            'by_account': display_details.groupby('account_name').agg({'value': 'sum'}).reset_index() if not display_details.empty else pd.DataFrame()
        }

    # ========== 数据日期 ==========
    st.markdown(f"""
        <div style='margin: 0 0 2rem 0; display: flex; align-items: baseline; gap: 15px;'>
            <h2 style='margin: 0; font-size: 1.7rem;'>{L.DASH_DATA_DATE} <span style='font-family: Outfit; font-weight: 700;'>{net_worth_data['latest_date']}</span></h2>
            <span style='color: var(--falcon-muted); font-size: 0.85rem; font-weight: 500;'>{L.DASH_BASED_ON}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # ========== 净值卡片 ==========
    btc_price = get_realtime_btc_price()
    btc_equivalent = net_worth_data['total_net_worth'] / btc_price if btc_price > 0 else 0
    
    render_net_worth_card(
        total_net_worth=net_worth_data['total_net_worth'],
        btc_equivalent=btc_equivalent,
        format_val=format_val,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    # ========== 目标进度 ==========
    goal = st.session_state.get('net_worth_goal', 500000)
    render_goal_progress(
        current_nw=net_worth_data['total_net_worth'],
        goal=goal,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    # ========== 汇总指标 ==========
    render_summary_metrics(
        transfers_data=transfers_data,
        pnl_data=pnl_data,
        benchmark_roi=benchmark_roi,
        format_val=format_val,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    # ========== 时间收益率 ==========
    render_time_returns_section(
        time_returns=time_returns,
        format_val=format_val,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    st.markdown("---")
    
    # ========== 时间筛选器 ==========
    st.markdown("##### 📈 数据可视化")
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    with filter_col1:
        time_filter = st.segmented_control(
            "时间筛选",
            options=["7D", "30D", "90D", "全部"],
            default="全部",
            label_visibility="collapsed"
        )
    
    # ========== 资产分布图表 ==========
    render_asset_charts(
        net_worth_data=net_worth_data,
        fx_rate=fx_rate,
        cur_sym=cur_sym
    )
    
    st.markdown("---")
    
    # ========== 历史曲线 ==========
    st.subheader(L.CHART_HISTORY)
    
    benchmark_options = ['S&P500', 'QQQ', 'BTC', '沪深300']
    selected_benchmarks = st.multiselect(
        "📊 对比基准",
        options=benchmark_options,
        default=[],
        help="选择要与您的资产组合进行对比的基准指数",
        placeholder="选择基准指数..."
    )
    
    history_df = calculations.get_net_worth_history(engine)
    
    render_history_chart(
        history_df=history_df,
        time_filter=time_filter,
        selected_benchmarks=selected_benchmarks,
        get_benchmark_history=calculations.get_benchmark_history,
        fx_rate=fx_rate,
        cur_sym=cur_sym
    )
    
    st.markdown("---")
    
    # ========== 月度热力图 ==========
    render_monthly_heatmap(
        history_df=history_df,
        fx_rate=fx_rate,
        cur_sym=cur_sym
    )
    
    st.markdown("---")
    
    # ========== 持仓明细 ==========
    render_holdings_table(
        net_worth_data=net_worth_data,
        fx_rate=fx_rate,
        cur_sym=cur_sym
    )
    
    st.markdown("---")
    
    # ========== 复盘日记 ==========
    render_journal_section(engine)
