"""
Dashboard Main Entry Point
Dashboard 主入口，整合所有组件
"""
from datetime import date, timedelta

import streamlit as st
import pandas as pd

from src import lang as L
from src import styles as S
from src.utils import get_realtime_btc_price
from src.config import MIN_DISPLAY_VALUE, DEFAULT_NET_WORTH_GOAL
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
    # Page header
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="margin: 0;">📊 仪表盘</h2>
        <p style="color: #64748B; font-size: 0.85rem; margin-top: 4px;">您的资产概览与分析</p>
    </div>
    """, unsafe_allow_html=True)
    
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
        display_details = filtered_details[filtered_details['value'] >= MIN_DISPLAY_VALUE]
        
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
            <h2 style='margin: 0; font-size: 1.7rem;'>{L.DASH_DATA_DATE} <span style="font-family: 'Outfit', sans-serif; font-weight: 700;">{net_worth_data['latest_date']}</span></h2>
            <span style='color: var(--falcon-muted); font-size: 0.85rem; font-weight: 500;'>{L.DASH_BASED_ON}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # ========== 净值卡片 ==========
    btc_price = get_realtime_btc_price()
    btc_equivalent = net_worth_data['total_net_worth'] / btc_price if btc_price > 0 else 0
    
    render_net_worth_card(
        total_net_worth=net_worth_data['total_net_worth'],
        btc_equivalent=btc_equivalent,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    # ========== 目标进度 ==========
    goal = st.session_state.get('net_worth_goal', DEFAULT_NET_WORTH_GOAL)
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
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    # ========== 时间收益率 ==========
    render_time_returns_section(
        time_returns=time_returns,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        privacy_on=privacy_on
    )
    
    # ========== 数据可视化 ==========
    st.markdown("""<div style='margin: 2.5rem 0 1.5rem; display: flex; align-items: center; gap: 12px;'><h3 style='margin: 0;'>📈 数据可视化</h3><div style='flex: 1; height: 1px; background: #E5E7EB;'></div></div>""", unsafe_allow_html=True)
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
    
    # ========== 历史曲线 ==========
    st.markdown(f"""<div style='margin: 2.5rem 0 1.5rem; display: flex; align-items: center; gap: 12px;'><h3 style='margin: 0;'>📉 {L.CHART_HISTORY}</h3><div style='flex: 1; height: 1px; background: #E5E7EB;'></div></div>""", unsafe_allow_html=True)
    
    # ---- 收藏基准管理 ----
    if 'favorite_benchmarks' not in st.session_state:
        st.session_state.favorite_benchmarks = []
    
    all_benchmarks = [
        'S&P500', 'QQQ', '罗素2000',
        'MAG7 ETF',
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
        'BTC', 'ETH',
        '沪深300', '恒生科技', '日经225',
        '黄金', '美债20年',
    ]
    
    # 分组定义（用于收藏管理面板显示）
    benchmark_groups = {
        '🇺🇸 美股大盘': ['S&P500', 'QQQ', '罗素2000'],
        '🏆 Mag 7': ['MAG7 ETF', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
        '🪙 加密': ['BTC', 'ETH'],
        '🌏 亚洲': ['沪深300', '恒生科技', '日经225'],
        '💎 另类': ['黄金', '美债20年'],
    }
    
    # 构建选项列表：收藏的排在前面
    favorites = [b for b in st.session_state.favorite_benchmarks if b in all_benchmarks]
    non_favorites = [b for b in all_benchmarks if b not in favorites]
    benchmark_options = favorites + non_favorites
    
    # ---- 基准对比面板 ----
    # 处理全选/清空 action
    if 'bench_action' not in st.session_state:
        st.session_state.bench_action = None
    
    bench_default = []
    if st.session_state.bench_action == 'all':
        bench_default = benchmark_options.copy()
        st.session_state.bench_action = None
    elif st.session_state.bench_action == 'clear':
        bench_default = []
        st.session_state.bench_action = None
    
    # 标题行 + 操作栏（垂直居中对齐）
    title_col, btn1_col, btn2_col, sort_col = st.columns(
        [3.5, 0.6, 0.6, 2.2], vertical_alignment="center"
    )
    
    with title_col:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.1rem;">📊</span>
            <span style="font-size: 0.95rem; font-weight: 700; color: var(--falcon-black); font-family: 'Outfit', sans-serif;">对比基准</span>
            <span class="falcon-badge blue" style="font-size: 0.65rem;">18 个可选</span>
        </div>
        """, unsafe_allow_html=True)
    
    with btn1_col:
        if st.button("全选", use_container_width=True, key="bench_select_all", type="tertiary"):
            st.session_state.bench_action = 'all'
            st.rerun()
    
    with btn2_col:
        if st.button("清空", use_container_width=True, key="bench_clear_all", type="tertiary"):
            st.session_state.bench_action = 'clear'
            st.rerun()
    
    with sort_col:
        sort_order = st.segmented_control(
            "排序",
            options=["默认", "收益↓", "收益↑"],
            default="默认",
            label_visibility="collapsed"
        )
    
    # 全宽选择器
    selected_benchmarks = st.multiselect(
        "对比基准",
        options=benchmark_options,
        default=bench_default,
        placeholder="🔍 搜索或选择基准...",
        format_func=lambda x: f"⭐ {x}" if x in favorites else x,
        label_visibility="collapsed"
    )
    
    # ---- 收藏管理（折叠区），按分组分类显示 ----
    with st.expander("⭐ 管理收藏基准 — 收藏的基准会自动置顶", expanded=False):
        new_favorites = []
        for group_label, group_items in benchmark_groups.items():
            st.markdown(f"<div style='font-size: 0.8rem; font-weight: 600; color: var(--falcon-muted); margin: 8px 0 4px; letter-spacing: 0.03em;'>{group_label}</div>", unsafe_allow_html=True)
            cols = st.columns(len(group_items))
            for j, bench in enumerate(group_items):
                with cols[j]:
                    if st.checkbox(bench, value=bench in favorites, key=f"fav_{bench}"):
                        new_favorites.append(bench)
        if new_favorites != favorites:
            st.session_state.favorite_benchmarks = new_favorites
    
    history_df = calculations.get_net_worth_history(engine)
    
    render_history_chart(
        history_df=history_df,
        time_filter=time_filter,
        selected_benchmarks=selected_benchmarks,
        get_benchmark_history=calculations.get_benchmark_history,
        fx_rate=fx_rate,
        cur_sym=cur_sym,
        sort_order=sort_order
    )
    
    st.markdown("""<div style='margin: 2rem 0 1.5rem; display: flex; align-items: center; gap: 12px;'><h3 style='margin: 0;'>🗓️ 月度分析</h3><div style='flex: 1; height: 1px; background: #E5E7EB;'></div></div>""", unsafe_allow_html=True)
    
    # ========== 月度热力图 ==========
    render_monthly_heatmap(
        history_df=history_df,
        fx_rate=fx_rate,
        cur_sym=cur_sym
    )
    
    st.markdown("""<div style='margin: 2rem 0 1.5rem; display: flex; align-items: center; gap: 12px;'><h3 style='margin: 0;'>📊 持仓明细</h3><div style='flex: 1; height: 1px; background: #E5E7EB;'></div></div>""", unsafe_allow_html=True)
    
    # ========== 持仓明细 ==========
    render_holdings_table(
        net_worth_data=net_worth_data,
        fx_rate=fx_rate,
        cur_sym=cur_sym
    )
    
    st.markdown("""<div style='margin: 2rem 0 1.5rem; display: flex; align-items: center; gap: 12px;'><h3 style='margin: 0;'>📝 复盘日记</h3><div style='flex: 1; height: 1px; background: #E5E7EB;'></div></div>""", unsafe_allow_html=True)
    
    # ========== 复盘日记 ==========
    render_journal_section(engine)
