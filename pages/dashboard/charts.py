"""
Dashboard Charts Components
图表渲染组件：资产分布、历史曲线、月度热力图
"""
from typing import Dict, Any, Optional, List, Callable
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src import lang as L
from src.styles import MODERN_COLORS


def get_chart_theme(dark_mode: bool) -> Dict[str, str]:
    """获取图表主题配置"""
    if dark_mode:
        return {
            'bg': 'rgba(0,0,0,0)',
            'paper_bg': 'rgba(0,0,0,0)',
            'font_color': '#E2E8F0',
            'grid_color': 'rgba(148, 163, 184, 0.2)',
            'line_color': '#334155'
        }
    return {
        'bg': 'rgba(0,0,0,0)',
        'paper_bg': 'rgba(0,0,0,0)',
        'font_color': '#1E293B',
        'grid_color': 'rgba(229, 231, 235, 0.5)',
        'line_color': '#E5E7EB'
    }


def render_asset_charts(
    net_worth_data: Dict[str, Any],
    fx_rate: float,
    cur_sym: str
) -> None:
    """
    渲染资产分布图表（Treemap 和饼图）
    
    Args:
        net_worth_data: 净值数据
        fx_rate: 汇率
        cur_sym: 货币符号
    """
    if net_worth_data['details'].empty or net_worth_data['details']['price'].sum() == 0:
        st.warning(L.CHART_MISSING_PRICE)
    
    col_chart1, col_chart2 = st.columns(2)
    
    # 资产分布 Treemap
    with col_chart1:
        st.subheader(L.CHART_ASSET_DIST)
        
        if not net_worth_data['by_symbol'].empty:
            chart_data = net_worth_data['by_symbol'].copy()
            chart_data['value'] = chart_data['value'] * fx_rate
            
            fig_treemap = px.treemap(
                chart_data,
                path=['symbol'],
                values='value',
                title=L.CHART_BY_ASSET,
                color='value',
                color_continuous_scale=['#E0F2FE', '#0EA5E9', '#1E3A8A'],
            )
            
            fig_treemap.update_traces(
                texttemplate='<b>%{label}</b><br>%{value:,.0f} ' + cur_sym,
                textfont=dict(size=14),
                hovertemplate='%{label}<br>' + cur_sym + '%{value:,.0f}<br>%{percentParent:.1%}<extra></extra>'
            )
            
            fig_treemap.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False
            )
            
            st.plotly_chart(fig_treemap, use_container_width=True)
        else:
            st.info(L.CHART_NO_DATA)
    
    # 账户分布饼图
    with col_chart2:
        st.subheader(L.CHART_ACCOUNT_DIST)
        
        if not net_worth_data['by_account'].empty:
            chart_data = net_worth_data['by_account'].copy()
            chart_data['value'] = chart_data['value'] * fx_rate
            
            fig_account = px.pie(
                chart_data,
                values='value',
                names='account_name',
                title=L.CHART_BY_ACCOUNT,
                hole=0.6,
                color_discrete_sequence=MODERN_COLORS[::-1]
            )
            
            fig_account.update_traces(
                texttemplate='%{percent:.1%}',
                hovertemplate='%{label}<br>%{value:,.0f} ' + cur_sym + '<br>%{percent:.2%}<extra></extra>'
            )
            
            fig_account.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12)
            )
            
            st.plotly_chart(fig_account, use_container_width=True)
        else:
            st.info(L.CHART_NO_DATA)


def render_history_chart(
    history_df: pd.DataFrame,
    time_filter: str,
    selected_benchmarks: List[str],
    get_benchmark_history: Callable,
    fx_rate: float,
    cur_sym: str,
    dark_mode: bool
) -> None:
    """
    渲染净值历史曲线图
    
    Args:
        history_df: 历史净值 DataFrame
        time_filter: 时间筛选（"7D", "30D", "90D", "全部"）
        selected_benchmarks: 选中的基准指数
        get_benchmark_history: 获取基准数据的函数
        fx_rate: 汇率
        cur_sym: 货币符号
        dark_mode: 深色模式开关
    """
    theme = get_chart_theme(dark_mode)
    
    if history_df.empty:
        st.info(L.CHART_NO_HISTORY)
        return
    
    if len(history_df) == 1:
        st.info(L.CHART_NEED_2)
        return
    
    # 应用时间筛选
    history_df_filtered = history_df.copy()
    if time_filter == "7D":
        cutoff_date = date.today() - timedelta(days=7)
        history_df_filtered = history_df_filtered[history_df_filtered['date'] >= cutoff_date]
    elif time_filter == "30D":
        cutoff_date = date.today() - timedelta(days=30)
        history_df_filtered = history_df_filtered[history_df_filtered['date'] >= cutoff_date]
    elif time_filter == "90D":
        cutoff_date = date.today() - timedelta(days=90)
        history_df_filtered = history_df_filtered[history_df_filtered['date'] >= cutoff_date]
    
    # 货币转换
    history_df_converted = history_df_filtered.copy()
    history_df_converted['net_worth'] = history_df_converted['net_worth'] * fx_rate
    
    # 检查筛选后数据是否足够
    if len(history_df_converted) < 2:
        st.info(f"选定时间范围内数据不足，显示全部历史数据")
        history_df_converted = history_df.copy()
        history_df_converted['net_worth'] = history_df_converted['net_worth'] * fx_rate
    
    # 检查是否所有值相同
    if history_df['net_worth'].nunique() == 1:
        st.warning("📊 所有历史日期的净值相同，可能是因为缺少历史价格数据。")
    
    fig_history = go.Figure()
    
    # 确定趋势颜色
    first_val = history_df_converted['net_worth'].iloc[0]
    last_val = history_df_converted['net_worth'].iloc[-1]
    is_up = last_val >= first_val
    
    line_color = '#10B981' if is_up else '#EF4444'
    fill_color = 'rgba(16, 185, 129, 0.15)' if is_up else 'rgba(239, 68, 68, 0.15)'
    
    use_pct_view = len(selected_benchmarks) > 0
    
    if use_pct_view:
        # 百分比视图模式
        history_df_converted['pct_change'] = ((history_df_converted['net_worth'] / first_val) - 1) * 100
        
        fig_history.add_trace(go.Scatter(
            x=history_df_converted['date'],
            y=history_df_converted['pct_change'],
            mode='lines+markers',
            name='我的组合',
            line=dict(color=line_color, width=3, shape='spline', smoothing=1.3),
            marker=dict(size=8, color='white', line=dict(color=line_color, width=2)),
            hovertemplate='<b>我的组合</b><br>%{y:.2f}%<extra></extra>'
        ))
        
        benchmark_colors = {
            'S&P500': '#6366F1',
            'QQQ': '#8B5CF6',
            'BTC': '#F59E0B',
            '沪深300': '#EF4444'
        }
        
        start_date = history_df_converted['date'].min()
        end_date = history_df_converted['date'].max()
        
        with st.spinner("📈 获取基准数据..."):
            benchmark_data = get_benchmark_history(start_date, end_date)
        
        for bench_name in selected_benchmarks:
            if bench_name in benchmark_data:
                bench_df = benchmark_data[bench_name].copy()
                
                if len(bench_df) > 0:
                    bench_start = bench_df['price'].iloc[0]
                    bench_df['pct_change'] = ((bench_df['price'] / bench_start) - 1) * 100
                    
                    fig_history.add_trace(go.Scatter(
                        x=bench_df['date'],
                        y=bench_df['pct_change'],
                        mode='lines',
                        name=bench_name,
                        line=dict(
                            color=benchmark_colors.get(bench_name, '#9CA3AF'),
                            width=2,
                            dash='dot'
                        ),
                        hovertemplate=f'<b>{bench_name}</b><br>' + '%{y:.2f}%<extra></extra>'
                    ))
        
        # 显示加载状态
        loaded = [b for b in selected_benchmarks if b in benchmark_data]
        not_loaded = [b for b in selected_benchmarks if b not in benchmark_data]
        if loaded:
            st.caption(f"✅ 已加载: {', '.join(loaded)}")
        if not_loaded:
            st.caption(f"⚠️ 无法获取: {', '.join(not_loaded)}")
        
        # 计算 Y 轴范围
        all_pct = history_df_converted['pct_change'].tolist()
        for bench_name in selected_benchmarks:
            if bench_name in benchmark_data and 'pct_change' in benchmark_data[bench_name].columns:
                all_pct.extend(benchmark_data[bench_name]['pct_change'].tolist())
        
        y_min_pct = min(all_pct) if all_pct else -5
        y_max_pct = max(all_pct) if all_pct else 5
        y_padding = (y_max_pct - y_min_pct) * 0.15
        
        fig_history.update_layout(
            title=dict(text="<b>收益率对比</b>", font=dict(size=20, family='Outfit', color='#1F2937'), x=0, xanchor='left'),
            yaxis=dict(
                title="收益率 %",
                ticksuffix="%",
                range=[y_min_pct - y_padding, y_max_pct + y_padding],
                showgrid=True,
                gridcolor='rgba(229, 231, 235, 0.6)',
                griddash='dot',
                zeroline=True,
                zerolinecolor='#9CA3AF',
                zerolinewidth=1
            )
        )
    else:
        # 绝对值视图
        y_min = history_df_converted['net_worth'].min()
        y_max = history_df_converted['net_worth'].max()
        y_range_padding = (y_max - y_min) * 0.15 if y_max != y_min else y_max * 0.05
        y_axis_min = max(0, y_min - y_range_padding)
        y_axis_max = y_max + y_range_padding
        
        fig_history.add_trace(go.Scatter(
            x=history_df_converted['date'],
            y=history_df_converted['net_worth'],
            mode='lines',
            line=dict(color=line_color, width=4, shape='spline', smoothing=1.3),
            fill='tozeroy',
            fillcolor=fill_color,
            hoverinfo='skip',
            showlegend=False
        ))
        
        fig_history.add_trace(go.Scatter(
            x=history_df_converted['date'],
            y=history_df_converted['net_worth'],
            mode='lines+markers',
            name='我的组合',
            line=dict(color=line_color, width=3, shape='spline', smoothing=1.3),
            marker=dict(size=10, color='white', line=dict(color=line_color, width=3)),
            hovertemplate='<b>%{x}</b><br>' + cur_sym + '%{y:,.0f}<extra></extra>'
        ))
        
        # 添加标注
        fig_history.add_annotation(
            x=history_df_converted['date'].iloc[0], y=first_val,
            text=f"{cur_sym}{first_val:,.0f}", showarrow=False, yshift=20,
            font=dict(size=11, color='#6B7280', family='Outfit'),
            bgcolor='rgba(255,255,255,0.8)', borderpad=4
        )
        fig_history.add_annotation(
            x=history_df_converted['date'].iloc[-1], y=last_val,
            text=f"<b>{cur_sym}{last_val:,.0f}</b>", showarrow=False, yshift=25,
            font=dict(size=13, color=line_color, family='Outfit'),
            bgcolor='rgba(255,255,255,0.9)', borderpad=4
        )
        
        fig_history.update_layout(
            title=dict(text=f"<b>{L.CHART_NW_OVER_TIME}</b>", font=dict(size=20, family='Outfit', color='#1F2937'), x=0, xanchor='left'),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(229, 231, 235, 0.6)',
                griddash='dot',
                zeroline=False,
                range=[y_axis_min, y_axis_max],
                tickprefix=cur_sym,
                tickformat=',.0f',
                side='right'
            )
        )
    
    # 通用布局
    has_benchmarks = len(selected_benchmarks) > 0
    chart_height = 500 if has_benchmarks else 420
    
    fig_history.update_layout(
        xaxis_title=None,
        yaxis_title=None,
        height=chart_height,
        margin=dict(l=20, r=20, t=70, b=80 if has_benchmarks else 20),
        paper_bgcolor=theme['paper_bg'],
        plot_bgcolor=theme['bg'],
        xaxis=dict(
            showgrid=False,
            linecolor=theme['line_color'],
            tickfont=dict(size=11, color=theme['font_color'], family='Inter'),
            tickformat='%m/%d',
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='#1E293B' if dark_mode else 'white',
            font_size=14,
            font_family='Inter',
            font_color='#E2E8F0' if dark_mode else '#1E293B',
            bordercolor=theme['line_color']
        ),
        showlegend=has_benchmarks,
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.18,
            xanchor='center',
            x=0.5,
            font=dict(size=9, family='Inter', color=theme['font_color']),
            bgcolor='rgba(30, 41, 59, 0.9)' if dark_mode else 'rgba(255,255,255,0.9)',
            bordercolor=theme['line_color'],
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig_history, use_container_width=True, config={'displayModeBar': False})
    
    # 统计指标
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        max_nw = history_df_converted['net_worth'].max()
        max_date = history_df_converted[history_df_converted['net_worth'] == max_nw]['date'].iloc[0]
        st.metric(L.CHART_ATH, f"{cur_sym}{max_nw:,.2f}", delta=f"{max_date}")
    
    with col_stat2:
        min_nw = history_df_converted['net_worth'].min()
        min_date = history_df_converted[history_df_converted['net_worth'] == min_nw]['date'].iloc[0]
        st.metric(L.CHART_ATL, f"{cur_sym}{min_nw:,.2f}", delta=f"{min_date}")
    
    with col_stat3:
        if len(history_df_converted) >= 2:
            growth = history_df_converted['net_worth'].iloc[-1] - history_df_converted['net_worth'].iloc[0]
            growth_pct = (growth / history_df_converted['net_worth'].iloc[0] * 100) if history_df_converted['net_worth'].iloc[0] > 0 else 0
            st.metric(L.CHART_GROWTH, f"{cur_sym}{growth:,.2f}", delta=f"{growth_pct:.2f}%")


def render_monthly_heatmap(
    history_df: pd.DataFrame,
    fx_rate: float,
    cur_sym: str,
    dark_mode: bool
) -> None:
    """
    渲染月度收益热力图
    
    Args:
        history_df: 历史净值 DataFrame
        fx_rate: 汇率
        cur_sym: 货币符号
        dark_mode: 深色模式开关
    """
    st.subheader("📅 月度收益热力图")
    
    theme = get_chart_theme(dark_mode)
    
    if history_df.empty or len(history_df) < 2:
        st.info("需要至少2个月的数据才能显示热力图")
        return
    
    history_df_temp = history_df.copy()
    history_df_temp['date'] = pd.to_datetime(history_df_temp['date'])
    history_df_temp = history_df_temp.sort_values('date')
    
    history_df_temp['year'] = history_df_temp['date'].dt.year
    history_df_temp['month'] = history_df_temp['date'].dt.month
    
    # 计算月度收益
    monthly_data = []
    for (year, month), group in history_df_temp.groupby(['year', 'month']):
        first_val = group['net_worth'].iloc[0]
        last_val = group['net_worth'].iloc[-1]
        change = last_val - first_val
        ret = ((change) / first_val * 100) if first_val > 0 else 0
        monthly_data.append({'year': year, 'month': month, 'return': ret, 'change': change})
    
    monthly_df = pd.DataFrame(monthly_data)
    
    if monthly_df.empty:
        st.info("需要至少2个月的数据才能显示热力图")
        return
    
    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    
    # 收益率 pivot
    pivot = monthly_df.pivot(index='year', columns='month', values='return')
    pivot = pivot.reindex(columns=range(1, 13), fill_value=None)
    pivot.columns = months
    
    # 金额变化 pivot
    pivot_change = monthly_df.pivot(index='year', columns='month', values='change')
    pivot_change = pivot_change.reindex(columns=range(1, 13), fill_value=None)
    pivot_change.columns = months
    
    year_labels = [str(int(y)) for y in pivot.index.tolist()]
    
    # 计算年度汇总
    yearly_summary = monthly_df.groupby('year').agg({
        'return': 'sum',
        'change': 'sum'
    }).reset_index()
    
    months_with_total = months + ['年度']
    pivot['年度'] = [yearly_summary[yearly_summary['year'] == int(y)]['return'].values[0] 
                    if int(y) in yearly_summary['year'].values else None 
                    for y in year_labels]
    pivot_change['年度'] = [yearly_summary[yearly_summary['year'] == int(y)]['change'].values[0] 
                           if int(y) in yearly_summary['year'].values else None 
                           for y in year_labels]
    
    # 格子内显示收益率百分比
    text_matrix = [[f"{v:+.1f}%" if pd.notna(v) else "" for v in row] for row in pivot.values]
    
    # 构建 hover 文本
    def format_change(val):
        if abs(val) >= 10000:
            return f"{val/1000:+,.1f}k"
        elif abs(val) >= 1000:
            return f"{val:+,.0f}"
        return f"{val:+.0f}"
    
    hover_matrix = []
    for i, row in enumerate(pivot.values):
        hover_row = []
        for j, v in enumerate(row):
            change_v = pivot_change.values[i][j] if j < len(pivot_change.values[i]) else None
            year = year_labels[i]
            col_name = months_with_total[j]
            if pd.notna(v) and pd.notna(change_v):
                change_display = change_v * fx_rate
                change_str = format_change(change_display)
                if col_name == '年度':
                    hover_row.append(f"<b>{year}年 全年汇总</b><br>累计收益率: {v:+.2f}%<br>累计收益额: {cur_sym}{change_str}")
                else:
                    hover_row.append(f"<b>{year}年 {col_name}</b><br>收益率: {v:+.2f}%<br>收益额: {cur_sym}{change_str}")
            elif pd.notna(v):
                hover_row.append(f"<b>{year}年 {col_name}</b><br>收益率: {v:+.2f}%")
            else:
                hover_row.append("")
        hover_matrix.append(hover_row)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=months_with_total,
        y=year_labels,
        colorscale=[
            [0, '#DC2626'],
            [0.35, '#FCA5A5'],
            [0.5, '#F3F4F6'],
            [0.65, '#6EE7B7'],
            [1, '#059669']
        ],
        zmid=0,
        text=text_matrix,
        texttemplate="%{text}",
        textfont={"size": 13, "family": "Outfit", "color": "#1F2937"},
        hovertext=hover_matrix,
        hovertemplate="%{hovertext}<extra></extra>",
        showscale=True,
        xgap=3,
        ygap=3,
        colorbar=dict(
            title=dict(text="收益率", side="right", font=dict(size=11)),
            ticksuffix="%",
            tickfont=dict(size=10),
            len=0.7,
            thickness=12,
            outlinewidth=0
        )
    ))
    
    fig_heatmap.update_layout(
        height=120 + len(pivot) * 70,
        margin=dict(l=60, r=100, t=50, b=20),
        paper_bgcolor=theme['paper_bg'],
        plot_bgcolor=theme['bg'],
        xaxis=dict(
            side='top',
            tickfont=dict(size=12, color=theme['font_color'], family='Inter'),
            tickangle=0
        ),
        yaxis=dict(
            tickfont=dict(size=14, color=theme['font_color'], family='Outfit'),
            autorange='reversed',
            type='category',
            tickmode='array',
            tickvals=year_labels,
            ticktext=year_labels
        )
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True, config={'displayModeBar': False})
    
    # 统计卡片
    _render_monthly_stats(monthly_df, fx_rate, cur_sym, dark_mode)


def _render_monthly_stats(
    monthly_df: pd.DataFrame,
    fx_rate: float,
    cur_sym: str,
    dark_mode: bool
) -> None:
    """渲染月度统计卡片"""
    positive_months = (monthly_df['return'] > 0).sum()
    total_months = len(monthly_df)
    avg_return = monthly_df['return'].mean()
    avg_change = monthly_df['change'].mean() * fx_rate
    best_month = monthly_df.loc[monthly_df['return'].idxmax()]
    worst_month = monthly_df.loc[monthly_df['return'].idxmin()]
    
    def format_change(val):
        if abs(val) >= 10000:
            return f"{val/1000:+,.1f}k"
        elif abs(val) >= 1000:
            return f"{val:+,.0f}"
        return f"{val:+.0f}"
    
    best_change = best_month['change'] * fx_rate
    worst_change = worst_month['change'] * fx_rate
    win_rate = positive_months / total_months * 100 if total_months > 0 else 0
    
    # 深色模式卡片样式
    worst_is_negative = worst_month['return'] < 0
    
    if dark_mode:
        card1_style = "background: linear-gradient(135deg, #064E3B 0%, #065F46 100%); border: 1px solid #059669;"
        card2_style = "background: linear-gradient(135deg, #1E3A5F 0%, #1E40AF 100%); border: 1px solid #3B82F6;"
        card3_style = "background: linear-gradient(135deg, #064E3B 0%, #047857 100%); border: 1px solid #10B981;"
        label1_color, value1_color = "#86EFAC", "#10B981"
        label2_color, value2_color = "#93C5FD", "#60A5FA"
        label3_color, value3_color = "#6EE7B7", "#10B981"
        if worst_is_negative:
            card4_style = "background: linear-gradient(135deg, #7F1D1D 0%, #991B1B 100%); border: 1px solid #EF4444;"
            label4_color, value4_color = "#FCA5A5", "#F87171"
            worst_detail_color = "#EF4444"
        else:
            card4_style = "background: linear-gradient(135deg, #78350F 0%, #92400E 100%); border: 1px solid #F59E0B;"
            label4_color, value4_color = "#FDE68A", "#FBBF24"
            worst_detail_color = "#F59E0B"
    else:
        card1_style = "background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%); border: 1px solid #86EFAC;"
        card2_style = "background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1px solid #93C5FD;"
        card3_style = "background: linear-gradient(135deg, #F0FDF4 0%, #D1FAE5 100%); border: 1px solid #6EE7B7;"
        label1_color, value1_color = "#15803D", "#166534"
        label2_color, value2_color = "#1D4ED8", "#1E40AF"
        label3_color, value3_color = "#047857", "#065F46"
        if worst_is_negative:
            card4_style = "background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%); border: 1px solid #FCA5A5;"
            label4_color, value4_color = "#B91C1C", "#991B1B"
            worst_detail_color = "#EF4444"
        else:
            card4_style = "background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%); border: 1px solid #FCD34D;"
            label4_color, value4_color = "#92400E", "#78350F"
            worst_detail_color = "#D97706"
    
    # 最差月份收益符号
    worst_return_str = f"{worst_month['return']:+.2f}%" if worst_is_negative else f"{worst_month['return']:.2f}%"
    
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 1.5rem 0;">
        <div class="u-card" style="padding: 20px; text-align: center; {card1_style}">
            <div style="font-size: 0.75rem; color: {label1_color}; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">平均月收益</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {value1_color}; font-family: Outfit; margin: 8px 0;">{avg_return:+.2f}%</div>
            <div style="font-size: 0.8rem; color: #22C55E;">{cur_sym}{format_change(avg_change)}/月</div>
        </div>
        <div class="u-card" style="padding: 20px; text-align: center; {card2_style}">
            <div style="font-size: 0.75rem; color: {label2_color}; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">盈利月份</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {value2_color}; font-family: Outfit; margin: 8px 0;">{positive_months}/{total_months}</div>
            <div style="font-size: 0.8rem; color: #3B82F6;">胜率 {win_rate:.0f}%</div>
        </div>
        <div class="u-card" style="padding: 20px; text-align: center; {card3_style}">
            <div style="font-size: 0.75rem; color: {label3_color}; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">🏆 最佳月份</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {value3_color}; font-family: Outfit; margin: 8px 0;">{int(best_month['year'])}/{int(best_month['month']):02d}</div>
            <div style="font-size: 0.85rem; color: #10B981; font-weight: 600;">+{best_month['return']:.2f}% ({cur_sym}{format_change(best_change)})</div>
        </div>
        <div class="u-card" style="padding: 20px; text-align: center; {card4_style}">
            <div style="font-size: 0.75rem; color: {label4_color}; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">📉 最差月份</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {value4_color}; font-family: Outfit; margin: 8px 0;">{int(worst_month['year'])}/{int(worst_month['month']):02d}</div>
            <div style="font-size: 0.85rem; color: {worst_detail_color}; font-weight: 600;">{worst_return_str} ({cur_sym}{format_change(worst_change)})</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
