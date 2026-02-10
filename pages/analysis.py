# -*- coding: utf-8 -*-
"""
收益分析页面 - 月度收益卡片 & 年化收益分析
支持隐私模式（隐藏具体金额，只显示百分比）
"""
from typing import Dict, Any, List, Optional
from datetime import date, timedelta, datetime
import calendar

import streamlit as st
import pandas as pd

from src import lang as L
from src.calculations import (
    calculate_current_net_worth,
    calculate_transfers_summary,
    calculate_pnl,
    calculate_time_based_returns,
    get_net_worth_history,
)
from src.utils import format_val


# ─────────────── 计算逻辑 ───────────────

def _compute_monthly_returns(history_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """从净值历史中计算逐月收益数据"""
    if history_df.empty or len(history_df) < 2:
        return []

    df = history_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

    monthly = []
    for (year, month), group in df.groupby(['year', 'month']):
        first_val = group['net_worth'].iloc[0]
        last_val = group['net_worth'].iloc[-1]
        change = last_val - first_val
        ret = ((change) / first_val * 100) if first_val > 0 else 0
        monthly.append({
            'year': int(year),
            'month': int(month),
            'start_nw': first_val,
            'end_nw': last_val,
            'change': change,
            'return_pct': ret,
            'data_points': len(group),
        })

    return monthly


def _compute_annualized_stats(
    monthly_data: List[Dict],
    time_returns: Dict[str, Any],
    pnl_data: Dict[str, Any],
) -> Dict[str, Any]:
    """汇总年化和综合统计"""
    if not monthly_data:
        return {'has_data': False}

    returns = [m['return_pct'] for m in monthly_data]
    changes = [m['change'] for m in monthly_data]
    positive = sum(1 for r in returns if r > 0)
    total = len(returns)

    # 按年度聚合
    yearly = {}
    for m in monthly_data:
        yearly.setdefault(m['year'], []).append(m)

    yearly_stats = []
    for year, months in sorted(yearly.items()):
        year_start = months[0]['start_nw']
        year_end = months[-1]['end_nw']
        year_change = year_end - year_start
        year_ret = ((year_change) / year_start * 100) if year_start > 0 else 0
        yearly_stats.append({
            'year': year,
            'start_nw': year_start,
            'end_nw': year_end,
            'change': year_change,
            'return_pct': year_ret,
            'months_count': len(months),
        })

    result = {
        'has_data': True,
        'avg_monthly_return': sum(returns) / total if total else 0,
        'avg_monthly_change': sum(changes) / total if total else 0,
        'best_month': max(monthly_data, key=lambda x: x['return_pct']),
        'worst_month': min(monthly_data, key=lambda x: x['return_pct']),
        'positive_months': positive,
        'total_months': total,
        'win_rate': positive / total * 100 if total else 0,
        'yearly': yearly_stats,
        'total_return_pct': pnl_data.get('roi_percentage', 0),
    }

    # 从 time_returns 取年化数据
    if time_returns.get('has_data'):
        result['apy'] = time_returns.get('apy', 0)
        result['apr'] = time_returns.get('apr', 0)
        result['roi'] = time_returns.get('roi', 0)
        result['days'] = time_returns.get('days', 0)
        result['start_date'] = time_returns.get('start_date')
        result['end_date'] = time_returns.get('end_date')
    else:
        result['apy'] = 0
        result['apr'] = 0
        result['roi'] = 0
        result['days'] = 0

    return result


# ─────────────── 渲染组件 ───────────────

MONTH_NAMES = ['', '1月', '2月', '3月', '4月', '5月', '6月',
               '7月', '8月', '9月', '10月', '11月', '12月']

MONTH_EMOJI = ['', '❄️', '🌸', '🌱', '🌷', '☀️', '🌞',
               '🌊', '🏖️', '🍂', '🎃', '🍁', '🎄']


def _format_amount(val: float, fx_rate: float, cur_sym: str) -> str:
    """格式化金额"""
    if abs(val) >= 1_000_000:
        return f"{cur_sym}{val * fx_rate / 1_000_000:+,.2f}M"
    elif abs(val) >= 10_000:
        return f"{cur_sym}{val * fx_rate / 1_000:+,.1f}K"
    elif abs(val) >= 1_000:
        return f"{cur_sym}{val * fx_rate:+,.0f}"
    return f"{cur_sym}{val * fx_rate:+,.2f}"


def _render_overview_cards(
    stats: Dict[str, Any],
    fx_rate: float,
    cur_sym: str,
    hide_amounts: bool,
    hide_amounts: bool,
) -> None:
    """渲染顶部概览卡片"""

    # 配色
    bg1 = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    bg2 = "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
    bg3 = "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
    text_primary = "#FFFFFF"
    text_muted = "rgba(255,255,255,0.75)"
    border = "rgba(255,255,255,0.2)"

    apy = stats.get('apy', 0)
    apr = stats.get('apr', 0)
    roi = stats.get('roi', 0)
    days = stats.get('days', 0)
    win_rate = stats.get('win_rate', 0)
    avg_ret = stats.get('avg_monthly_return', 0)
    avg_change = stats.get('avg_monthly_change', 0)

    apy_color = "#10B981" if apy >= 0 else "#EF4444"
    roi_color = "#10B981" if roi >= 0 else "#EF4444"

    # 平均月收益显示
    avg_display = f"{avg_ret:+.2f}%"
    if not hide_amounts:
        avg_amount = _format_amount(avg_change, fx_rate, cur_sym)
        avg_display += f"<br><span style='font-size: 0.85rem; opacity: 0.85;'>{avg_amount}/月</span>"

    st.markdown(f"""
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 2rem;">
    <!-- 年化收益率 -->
    <div style="background: {bg1}; border-radius: 20px; padding: 28px 24px; border: 1px solid {border};
                box-shadow: 0 10px 40px rgba(102,126,234,0.25); position: relative; overflow: hidden;">
        <div style="position: absolute; top: -20px; right: -20px; width: 100px; height: 100px;
                    background: rgba(255,255,255,0.08); border-radius: 50%;"></div>
        <div style="position: absolute; bottom: -30px; left: -10px; width: 70px; height: 70px;
                    background: rgba(255,255,255,0.05); border-radius: 50%;"></div>
        <div style="font-size: 0.78rem; color: {text_muted}; text-transform: uppercase;
                    letter-spacing: 0.1em; font-weight: 600; margin-bottom: 12px;">
            📈 复利年化 (APY)
        </div>
        <div style="font-size: 2.6rem; font-weight: 800; color: {text_primary};
                    font-family: 'Outfit', sans-serif; line-height: 1.1;">
            {apy:+.2f}%
        </div>
        <div style="margin-top: 12px; font-size: 0.8rem; color: {text_muted};">
            简单年化 APR: {apr:+.2f}%
        </div>
        <div style="margin-top: 4px; font-size: 0.78rem; color: {text_muted};">
            运行 {days} 天
        </div>
    </div>

    <!-- 总收益率 -->
    <div style="background: {bg2}; border-radius: 20px; padding: 28px 24px; border: 1px solid {border};
                box-shadow: 0 10px 40px rgba(240,147,251,0.2); position: relative; overflow: hidden;">
        <div style="position: absolute; top: -15px; right: -15px; width: 80px; height: 80px;
                    background: rgba(255,255,255,0.1); border-radius: 50%;"></div>
        <div style="font-size: 0.78rem; color: {text_muted}; text-transform: uppercase;
                    letter-spacing: 0.1em; font-weight: 600; margin-bottom: 12px;">
            🏆 累计 ROI
        </div>
        <div style="font-size: 2.6rem; font-weight: 800; color: {text_primary};
                    font-family: 'Outfit', sans-serif; line-height: 1.1;">
            {roi:+.2f}%
        </div>
        <div style="margin-top: 12px; font-size: 0.8rem; color: {text_muted};">
            胜率: {win_rate:.0f}% ({stats.get('positive_months', 0)}/{stats.get('total_months', 0)} 月)
        </div>
    </div>

    <!-- 月均收益 -->
    <div style="background: {bg3}; border-radius: 20px; padding: 28px 24px; border: 1px solid {border};
                box-shadow: 0 10px 40px rgba(79,172,254,0.2); position: relative; overflow: hidden;">
        <div style="position: absolute; top: -25px; right: -10px; width: 90px; height: 90px;
                    background: rgba(255,255,255,0.08); border-radius: 50%;"></div>
        <div style="font-size: 0.78rem; color: {text_muted}; text-transform: uppercase;
                    letter-spacing: 0.1em; font-weight: 600; margin-bottom: 12px;">
            📊 月均收益
        </div>
        <div style="font-size: 2.2rem; font-weight: 800; color: {text_primary};
                    font-family: 'Outfit', sans-serif; line-height: 1.2;">
            {avg_display}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def _render_yearly_cards(
    stats: Dict[str, Any],
    fx_rate: float,
    cur_sym: str,
    hide_amounts: bool,
    cur_sym: str,
    hide_amounts: bool,
) -> None:
    """渲染年度汇总卡片"""
    yearly = stats.get('yearly', [])
    if not yearly:
        return

    st.markdown("##### 📅 年度汇总")

    cols = st.columns(min(len(yearly), 4))
    for i, ys in enumerate(reversed(yearly)):
        with cols[i % len(cols)]:
            ret = ys['return_pct']
            is_positive = ret >= 0
            icon = "📈" if is_positive else "📉"

            if is_positive:
                card_bg = "linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)"
                accent = "#059669"
                border_c = "#86EFAC"
            else:
                card_bg = "linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)"
                accent = "#DC2626"
                border_c = "#FCA5A5"

            amount_html = ""
            if not hide_amounts:
                amount_str = _format_amount(ys['change'], fx_rate, cur_sym)
                amount_html = f"""<div style="font-size: 0.85rem; color: {accent}; margin-top: 4px;
                                             font-weight: 600;">{amount_str}</div>"""

            st.markdown(f"""
<div style="background: {card_bg}; border-radius: 16px; padding: 22px 20px;
            border: 1px solid {border_c}; text-align: center; margin-bottom: 16px;
            transition: transform 0.2s; cursor: default;"
     onmouseover="this.style.transform='translateY(-3px)'"
     onmouseout="this.style.transform='translateY(0)'">
    <div style="font-size: 0.75rem; color: var(--falcon-muted); text-transform: uppercase;
                font-weight: 600; letter-spacing: 0.08em;">{icon} {ys['year']}年</div>
    <div style="font-size: 2rem; font-weight: 800; color: {accent};
                font-family: 'Outfit', sans-serif; margin: 8px 0;">
        {ret:+.2f}%
    </div>
    {amount_html}
    <div style="font-size: 0.7rem; color: var(--falcon-muted); margin-top: 6px;">
        {ys['months_count']} 个月数据
    </div>
</div>
""", unsafe_allow_html=True)


def _render_monthly_cards(
    monthly_data: List[Dict],
    fx_rate: float,
    cur_sym: str,
    hide_amounts: bool,
    fx_rate: float,
    cur_sym: str,
    hide_amounts: bool,
    selected_year: Optional[int] = None,
) -> None:
    """渲染月度收益卡片网格"""
    if not monthly_data:
        st.info("暂无月度数据")
        return

    # 按年筛选
    if selected_year:
        filtered = [m for m in monthly_data if m['year'] == selected_year]
    else:
        filtered = monthly_data

    if not filtered:
        st.info(f"{selected_year}年 暂无数据")
        return

    # 按时间倒序
    filtered = sorted(filtered, key=lambda x: (x['year'], x['month']), reverse=True)

    st.markdown("##### 📋 月度明细卡片")

    # 3列网格
    for row_start in range(0, len(filtered), 3):
        row_items = filtered[row_start: row_start + 3]
        cols = st.columns(3)

        for col_idx, m_data in enumerate(row_items):
            with cols[col_idx]:
                ret = m_data['return_pct']
                change = m_data['change']
                is_positive = ret >= 0
                month_name = MONTH_NAMES[m_data['month']]
                emoji = MONTH_EMOJI[m_data['month']]

                # 卡片颜色
                if is_positive:
                    if ret > 10:
                        gradient = "linear-gradient(135deg, #059669 0%, #10B981 50%, #34D399 100%)"
                        text_color = "#FFFFFF"
                        badge_bg = "rgba(255,255,255,0.2)"
                    elif ret > 5:
                        gradient_a = "#F0FDF4"
                        gradient_b = "#DCFCE7"
                        gradient = f"linear-gradient(135deg, {gradient_a} 0%, {gradient_b} 100%)"
                        text_color = "#10B981"
                        badge_bg = "rgba(16, 185, 129, 0.15)"
                    else:
                        gradient_a = "#F8FAFC"
                        gradient_b = "#F0FDF4"
                        gradient = f"linear-gradient(135deg, {gradient_a} 0%, {gradient_b} 100%)"
                        text_color = "#10B981"
                        badge_bg = "rgba(16, 185, 129, 0.1)"
                else:
                    if ret < -10:
                        gradient = "linear-gradient(135deg, #DC2626 0%, #EF4444 50%, #F87171 100%)"
                        text_color = "#FFFFFF"
                        badge_bg = "rgba(255,255,255,0.2)"
                    elif ret < -5:
                        gradient_a = "#FEF2F2"
                        gradient_b = "#FEE2E2"
                        gradient = f"linear-gradient(135deg, {gradient_a} 0%, {gradient_b} 100%)"
                        text_color = "#EF4444"
                        badge_bg = "rgba(239, 68, 68, 0.15)"
                    else:
                        gradient_a = "#F8FAFC"
                        gradient_b = "#FEF2F2"
                        gradient = f"linear-gradient(135deg, {gradient_a} 0%, {gradient_b} 100%)"
                        text_color = "#EF4444"
                        badge_bg = "rgba(239, 68, 68, 0.1)"

                # 收益额显示
                amount_html = ""
                if not hide_amounts:
                    amount_str = _format_amount(change, fx_rate, cur_sym)
                    amount_html = f"""
                    <div style="font-size: 0.9rem; color: {text_color}; margin-top: 6px;
                                font-weight: 600; opacity: 0.9;">
                        {amount_str}
                    </div>"""

                # 期初/期末净值
                nw_html = ""
                if not hide_amounts:
                    start_str = f"{cur_sym}{m_data['start_nw'] * fx_rate:,.0f}"
                    end_str = f"{cur_sym}{m_data['end_nw'] * fx_rate:,.0f}"
                    nw_html = f"""
                    <div style="display: flex; justify-content: space-between; margin-top: 12px;
                                padding-top: 10px; border-top: 1px solid rgba(128,128,128,0.2);
                                font-size: 0.72rem; color: var(--falcon-muted);">
                        <span>期初 {start_str}</span>
                        <span>期末 {end_str}</span>
                    </div>"""

                # 箭头方向
                arrow = "↗" if is_positive else "↘" if ret < 0 else "→"

                st.markdown(f"""
<div style="background: {gradient}; border-radius: 18px; padding: 24px 20px;
            margin-bottom: 16px; position: relative; overflow: hidden;
            transition: all 0.3s ease; cursor: default;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);"
     onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 30px rgba(0,0,0,0.15)'"
     onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0,0,0,0.08)'">

    <!-- 装饰圆 -->
    <div style="position: absolute; top: -15px; right: -15px; width: 60px; height: 60px;
                background: rgba(255,255,255,0.08); border-radius: 50%;"></div>

    <!-- 头部: 月份标签 -->
    <div style="display: flex; justify-content: space-between; align-items: center;
                margin-bottom: 14px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.5rem;">{emoji}</span>
            <div>
                <div style="font-size: 1rem; font-weight: 700; color: {text_color};
                            font-family: 'Outfit', sans-serif;">
                    {m_data['year']}.{m_data['month']:02d}
                </div>
                <div style="font-size: 0.72rem; color: {text_color}; opacity: 0.7;">
                    {month_name}
                </div>
            </div>
        </div>
        <div style="background: {badge_bg}; border-radius: 10px; padding: 4px 10px;
                    font-size: 0.75rem; font-weight: 600; color: {text_color};">
            {arrow} {ret:+.1f}%
        </div>
    </div>

    <!-- 核心数值 -->
    <div style="font-size: 2rem; font-weight: 800; color: {text_color};
                font-family: 'Outfit', sans-serif; line-height: 1.1;">
        {ret:+.2f}%
    </div>

    {amount_html}
    {nw_html}
</div>
""", unsafe_allow_html=True)


def _render_extremes(
    stats: Dict[str, Any],
    fx_rate: float,
    cur_sym: str,
    hide_amounts: bool,
    cur_sym: str,
    hide_amounts: bool,
) -> None:
    """渲染最佳/最差月份对比"""
    best = stats.get('best_month')
    worst = stats.get('worst_month')
    if not best or not worst:
        return

    st.markdown("##### 🏅 极值对比")

    col1, col2 = st.columns(2)

    for col, data, label, colors in [
        (col1, best, "🏆 最佳月份", {
            'light_bg': "linear-gradient(135deg, #F0FDF4 0%, #D1FAE5 100%)",
            'accent': "#10B981",
            'light_border': "#6EE7B7",
        }),
        (col2, worst, "📉 最差月份", {
            'light_bg': "linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)" if worst['return_pct'] < 0 else "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)",
            'accent': "#EF4444" if worst['return_pct'] < 0 else "#F59E0B",
            'light_border': "#FCA5A5" if worst['return_pct'] < 0 else "#FCD34D",
        }),
    ]:
        with col:
            bg = colors['light_bg']
            border_c = colors['light_border']
            accent = colors['accent']

            amount_html = ""
            if not hide_amounts:
                amt = _format_amount(data['change'], fx_rate, cur_sym)
                amount_html = f"""<div style="font-size: 1rem; color: {accent}; font-weight: 600;
                                             margin-top: 4px;">{amt}</div>"""

            st.markdown(f"""
<div style="background: {bg}; border-radius: 18px; padding: 26px 22px;
            border: 1px solid {border_c}; text-align: center; margin-bottom: 20px;
            transition: transform 0.2s;"
     onmouseover="this.style.transform='scale(1.02)'"
     onmouseout="this.style.transform='scale(1)'">
    <div style="font-size: 0.78rem; color: var(--falcon-muted); text-transform: uppercase;
                font-weight: 600; letter-spacing: 0.08em; margin-bottom: 10px;">
        {label}
    </div>
    <div style="font-size: 1.4rem; font-weight: 700; color: {accent};
                font-family: 'Outfit', sans-serif;">
        {data['year']}/{data['month']:02d}
    </div>
    <div style="font-size: 2.2rem; font-weight: 800; color: {accent};
                font-family: 'Outfit', sans-serif; margin: 6px 0;">
        {data['return_pct']:+.2f}%
    </div>
    {amount_html}
</div>
""", unsafe_allow_html=True)


# ─────────────── 页面主入口 ───────────────

def show_analysis_page(
    engine,
    privacy_on: bool = False,
    fx_rate: float = 1.0,
    cur_sym: str = "$",
) -> None:
    """
    收益分析页面主入口

    Args:
        engine: 数据库引擎
        privacy_on: 全局隐私模式开关
        fx_rate: 汇率
        cur_sym: 货币符号
    """
    st.markdown("---")

    # 页面级隐藏金额开关 (独立于全局隐私模式)
    col_title, col_toggle = st.columns([3, 1])
    with col_title:
        st.markdown("""
<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 0.5rem;">
    <span style="font-size: 2rem;">📊</span>
    <div>
        <div style="font-size: 1.5rem; font-weight: 800; font-family: 'Outfit', sans-serif;
                    color: var(--falcon-black);">收益分析</div>
        <div style="font-size: 0.85rem; color: var(--falcon-muted);">
            月度收益 · 年化回报 · 趋势洞察
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
    with col_toggle:
        hide_amounts = st.toggle(
            "🔒 隐藏金额",
            value=privacy_on,
            help="开启后只显示收益率百分比，隐藏具体金额"
        )

    # ========== 数据加载 ==========
    with st.spinner("📊 正在计算收益数据..."):
        history_df = get_net_worth_history(engine)
        time_returns = calculate_time_based_returns(engine)
        pnl_data = calculate_pnl(engine)

    if history_df.empty or len(history_df) < 2:
        st.info("📭 需要至少两次快照数据才能进行收益分析。请先在数据录入页添加快照。")
        return

    # ========== 计算 ==========
    monthly_data = _compute_monthly_returns(history_df)
    stats = _compute_annualized_stats(monthly_data, time_returns, pnl_data)

    if not stats.get('has_data'):
        st.info("暂无足够数据进行分析")
        return

    # ========== 渲染：概览卡片 ==========
    _render_overview_cards(stats, fx_rate, cur_sym, hide_amounts)

    st.markdown("---")

    # ========== 渲染：年度汇总 ==========
    _render_yearly_cards(stats, fx_rate, cur_sym, hide_amounts)

    st.markdown("---")

    # ========== 渲染：极值对比 ==========
    _render_extremes(stats, fx_rate, cur_sym, hide_amounts)

    st.markdown("---")

    # ========== 年份筛选 ==========
    years = sorted(set(m['year'] for m in monthly_data), reverse=True)
    year_options = ["全部"] + [str(y) for y in years]

    filter_col, _, _ = st.columns([1, 1, 2])
    with filter_col:
        selected_year_str = st.selectbox(
            "选择年份",
            year_options,
            index=0,
            label_visibility="collapsed"
        )

    selected_year = int(selected_year_str) if selected_year_str != "全部" else None

    # ========== 渲染：月度卡片 ==========
    _render_monthly_cards(monthly_data, fx_rate, cur_sym, hide_amounts, selected_year)
