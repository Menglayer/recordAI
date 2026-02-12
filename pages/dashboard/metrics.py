"""
Dashboard Metrics Components
净值卡片、目标进度、汇总指标等组件
"""
from typing import Optional
import streamlit as st
from src import styles as S
from src import lang as L
from src.utils import format_val


def render_net_worth_card(
    total_net_worth: float,
    btc_equivalent: float,
    fx_rate: float,
    cur_sym: str,
    privacy_on: bool
) -> None:
    """
    渲染净值卡片
    
    Args:
        total_net_worth: 总净值
        btc_equivalent: BTC 等值
        fx_rate: 汇率
        cur_sym: 货币符号
        privacy_on: 隐私模式开关
    """
    S.metric_card(
        label=L.DASH_NET_WORTH,
        value=format_val(total_net_worth, fx_rate, cur_sym, privacy_on),
        is_masked=privacy_on,
        subtitle=f"{btc_equivalent:.4f} BTC"
    )


def render_goal_progress(
    current_nw: float,
    goal: float,
    fx_rate: float,
    cur_sym: str,
    privacy_on: bool
) -> None:
    """
    渲染目标进度条
    
    Args:
        current_nw: 当前净值
        goal: 目标净值
        fx_rate: 汇率
        cur_sym: 货币符号
        privacy_on: 隐私模式开关
    """
    progress = min(current_nw / goal, 1.0) if goal > 0 else 0
    progress_pct = progress * 100
    remaining = max(0, goal - current_nw)
    
    # 确定状态和颜色
    if progress >= 1:
        status_icon = "🎉"
        status_text = "恭喜！目标达成！"
        gradient = "linear-gradient(90deg, #10B981, #34D399, #6EE7B7)"
        glow_color = "rgba(16, 185, 129, 0.4)"
    elif progress >= 0.75:
        status_icon = "🔥"
        status_text = f"冲刺中！还差 {cur_sym}{remaining * fx_rate:,.0f}"
        gradient = "linear-gradient(90deg, #0EA5E9, #38BDF8, #7DD3FC)"
        glow_color = "rgba(14, 165, 233, 0.4)"
    elif progress >= 0.5:
        status_icon = "📈"
        status_text = f"进展顺利！还差 {cur_sym}{remaining * fx_rate:,.0f}"
        gradient = "linear-gradient(90deg, #6366F1, #818CF8, #A5B4FC)"
        glow_color = "rgba(99, 102, 241, 0.4)"
    else:
        status_icon = "🎯"
        status_text = f"努力中！还差 {cur_sym}{remaining * fx_rate:,.0f}"
        gradient = "linear-gradient(90deg, #F59E0B, #FBBF24, #FDE047)"
        glow_color = "rgba(245, 158, 11, 0.4)"
    
    if not privacy_on:
        st.markdown(f"""
            <div class="u-card" style="padding: 1.5rem; margin: 0.5rem 0 2rem 0; position: relative; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 2rem; animation: bounce 1s infinite;">{status_icon}</span>
                        <div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #1F2937;">目标进度</div>
                            <div style="font-size: 0.8rem; color: #6B7280; margin-top: 2px;">{status_text}</div>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 2.5rem; font-weight: 800; font-family: Outfit; background: {gradient}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: pulse 2s infinite;">{progress_pct:.1f}%</div>
                    </div>
                </div>
                <div style="background: #E5E7EB; border-radius: 16px; height: 28px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1); position: relative;">
                    <div class="progress-fill" style="background: {gradient}; width: {progress_pct}%; height: 100%; border-radius: 16px; position: relative; box-shadow: 0 0 20px {glow_color}, 0 0 40px {glow_color}; animation: glow 2s ease-in-out infinite;">
                        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.5) 50%, transparent 100%); animation: shine 2s ease-in-out infinite;"></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 14px; font-size: 0.85rem;">
                    <div style="text-align: left;">
                        <div style="color: #9CA3AF; font-size: 0.7rem; text-transform: uppercase;">当前</div>
                        <div style="font-weight: 700; color: #374151; font-family: Outfit;">{cur_sym}{current_nw * fx_rate:,.0f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: #9CA3AF; font-size: 0.7rem; text-transform: uppercase;">进度</div>
                        <div style="font-weight: 700; color: #374151;">{progress_pct:.1f}%</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #9CA3AF; font-size: 0.7rem; text-transform: uppercase;">目标</div>
                        <div style="font-weight: 700; color: #374151; font-family: Outfit;">{cur_sym}{goal * fx_rate:,.0f}</div>
                    </div>
                </div>
            </div>
            <style>
                @keyframes shine {{
                    0% {{ transform: translateX(-100%); }}
                    50% {{ transform: translateX(100%); }}
                    100% {{ transform: translateX(100%); }}
                }}
                @keyframes glow {{
                    0%, 100% {{ box-shadow: 0 0 15px {glow_color}, 0 0 30px {glow_color}; }}
                    50% {{ box-shadow: 0 0 25px {glow_color}, 0 0 50px {glow_color}; }}
                }}
                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.8; }}
                }}
                @keyframes bounce {{
                    0%, 100% {{ transform: translateY(0); }}
                    50% {{ transform: translateY(-5px); }}
                }}
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="u-card" style="padding: 1.5rem; margin: 0.5rem 0 2rem 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 2rem;">🎯</span>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #1F2937;">目标进度</div>
                    </div>
                    <span style="font-size: 1.5rem; font-weight: 600;">••••••</span>
                </div>
                <div style="background: #E5E7EB; border-radius: 16px; height: 28px;"></div>
            </div>
        """, unsafe_allow_html=True)


def render_summary_metrics(
    transfers_data: dict,
    pnl_data: dict,
    benchmark_roi: Optional[float],
    fx_rate: float,
    cur_sym: str,
    privacy_on: bool
) -> None:
    """
    渲染汇总指标卡片（投入资金、盈亏、ROI）
    
    Args:
        transfers_data: 转账汇总数据
        pnl_data: 盈亏数据
        benchmark_roi: 基准收益率
        fx_rate: 汇率
        cur_sym: 货币符号
        privacy_on: 隐私模式开关
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        S.metric_card(
            label=L.DASH_INVESTED,
            value=format_val(transfers_data['net_investment'], fx_rate, cur_sym, privacy_on),
            delta=f"{format_val(transfers_data['total_deposits'], fx_rate, cur_sym, privacy_on)} 入 | {format_val(transfers_data['total_withdrawals'], fx_rate, cur_sym, privacy_on)} 出",
            delta_up="neutral",
            is_masked=privacy_on
        )
    
    with col2:
        pnl_value = pnl_data['unrealized_pnl']
        S.metric_card(
            label=L.DASH_PNL,
            value=format_val(pnl_value, fx_rate, cur_sym, privacy_on),
            delta=f"{pnl_data['roi_percentage']:.2f}%",
            delta_up=pnl_value >= 0,
            is_masked=privacy_on,
            benchmark=f"BTC {benchmark_roi:+.1f}%" if (benchmark_roi is not None and benchmark_roi != 0) else None
        )
    
    with col3:
        roi_pct = pnl_data['roi_percentage']
        S.metric_card(
            label=L.DASH_ROI,
            value=f"{roi_pct:.2f}%",
            delta=L.DASH_PROFIT if roi_pct > 0 else L.DASH_LOSS if roi_pct < 0 else L.DASH_EVEN,
            delta_up=roi_pct >= 0
        )
