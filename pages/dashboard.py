"""
Dashboard page - Main overview with charts and metrics
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from src import lang as L
from src import styles as S


def show_dashboard(
    engine,
    privacy_on=False,
    fx_rate=1.0,
    cur_sym="$",
    calculate_current_net_worth=None,
    calculate_transfers_summary=None,
    calculate_pnl=None,
    calculate_time_based_returns=None,
    get_benchmark_roi=None,
    get_net_worth_history=None,
    get_benchmark_history=None,
    format_val=None
):
    """Dashboard page with Benchmarking"""
    st.markdown("---")
    
    # Loading spinner while calculating data
    with st.spinner("📊 正在加载数据..."):
        net_worth_data = calculate_current_net_worth(engine)
        transfers_data = calculate_transfers_summary(engine)
        pnl_data = calculate_pnl(engine)
        time_returns = calculate_time_based_returns(engine)
        benchmark_roi = get_benchmark_roi(engine)
    
    # Filter out archived accounts from current display
    archived = st.session_state.get('archived_accounts', [])
    if not net_worth_data['details'].empty:
        filtered_details = net_worth_data['details'].copy()
        
        # Filter out archived accounts
        if archived:
            filtered_details = filtered_details[~filtered_details['account_name'].isin(archived)]
        
        # Filter out accounts with value < $10 for display (but keep in total)
        total_net_worth = filtered_details['value'].sum() if not filtered_details.empty else 0
        display_details = filtered_details[filtered_details['value'] >= 10]
        
        # Recalculate display data (excluding small accounts from charts)
        net_worth_data = {
            'latest_date': net_worth_data['latest_date'],
            'total_net_worth': total_net_worth,
            'details': display_details,
            'by_symbol': display_details.groupby('symbol').agg({'quantity': 'sum', 'value': 'sum'}).reset_index() if not display_details.empty else pd.DataFrame(),
            'by_account': display_details.groupby('account_name').agg({'value': 'sum'}).reset_index() if not display_details.empty else pd.DataFrame()
        }

    # Data date - Enhanced Typography
    st.markdown(f"""
        <div style='margin: 0 0 2rem 0; display: flex; align-items: baseline; gap: 15px;'>
            <h2 style='margin: 0; font-size: 1.7rem;'>{L.DASH_DATA_DATE} <span style='font-family: Outfit; font-weight: 700;'>{net_worth_data['latest_date']}</span></h2>
            <span style='color: var(--falcon-muted); font-size: 0.85rem; font-weight: 500;'>{L.DASH_BASED_ON}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Net Worth prominently with BTC equivalent
    # Get realtime BTC price for conversion
    from src.utils import get_realtime_btc_price
    btc_price = get_realtime_btc_price()
    
    btc_equivalent = net_worth_data['total_net_worth'] / btc_price if btc_price > 0 else 0
    
    S.metric_card(
        label=L.DASH_NET_WORTH,
        value=format_val(net_worth_data['total_net_worth'], fx_rate, cur_sym, privacy_on),
        is_masked=privacy_on,
        subtitle=f"{btc_equivalent:.4f} BTC"
    )
    
    # Goal Progress Bar - Premium Design
    goal = st.session_state.get('net_worth_goal', 500000)
    current_nw = net_worth_data['total_net_worth']
    progress = min(current_nw / goal, 1.0) if goal > 0 else 0
    progress_pct = progress * 100
    remaining = max(0, goal - current_nw)
    
    # Determine status and colors
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
    
    # Other metrics in one row
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
    
    # Time-based returns
    if time_returns['has_data']:
        st.markdown("---")
        st.subheader(L.TIME_RETURNS)
        
        # Privacy helper
        def mask(val):
            return "••••••" if privacy_on else val
        
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
    
    st.markdown("---")
    
    # Time Period Filter
    st.markdown("##### 📈 数据可视化")
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    with filter_col1:
        time_filter = st.segmented_control(
            "时间筛选",
            options=["7D", "30D", "90D", "全部"],
            default="全部",
            label_visibility="collapsed"
        )
    
    # Charts
    if net_worth_data['details'].empty or net_worth_data['details']['price'].sum() == 0:
        st.warning(L.CHART_MISSING_PRICE)
    
    MODERN_COLORS = ['#10B981', '#F97316', '#0EA5E9', '#6366F1', '#F59E0B', '#EC4899', '#8B5CF6', '#14B8A6', '#F43F5E']
    
    col_chart1, col_chart2 = st.columns(2)
    
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
    
    st.markdown("---")
    
    # History chart
    st.subheader(L.CHART_HISTORY)
    
    # Benchmark selector
    benchmark_options = ['S&P500', 'QQQ', 'BTC', '沪深300']
    selected_benchmarks = st.multiselect(
        "📊 对比基准",
        options=benchmark_options,
        default=[],
        help="选择要与您的资产组合进行对比的基准指数",
        placeholder="选择基准指数..."
    )
    
    history_df = get_net_worth_history(engine)
    
    if not history_df.empty and len(history_df) > 1:
        # Apply time filter
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
        
        # Apply currency conversion
        history_df_converted = history_df_filtered.copy()
        history_df_converted['net_worth'] = history_df_converted['net_worth'] * fx_rate
        
        # Check if we have enough data after filtering
        if len(history_df_converted) < 2:
            st.info(f"选定时间范围内数据不足，显示全部历史数据")
            history_df_converted = history_df.copy()
            history_df_converted['net_worth'] = history_df_converted['net_worth'] * fx_rate
        
        # Check if all values are the same
        unique_values = history_df['net_worth'].nunique()
        
        if unique_values == 1:
            st.warning("📊 所有历史日期的净值相同，可能是因为缺少历史价格数据。")
        
        fig_history = go.Figure()
        
        # Determine trend color
        first_val = history_df_converted['net_worth'].iloc[0]
        last_val = history_df_converted['net_worth'].iloc[-1]
        is_up = last_val >= first_val
        
        if is_up:
            line_color = '#10B981'
            fill_color = 'rgba(16, 185, 129, 0.15)'
        else:
            line_color = '#EF4444'
            fill_color = 'rgba(239, 68, 68, 0.15)'
        
        use_pct_view = len(selected_benchmarks) > 0
        
        if use_pct_view:
            # Percentage view mode
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
            
            loaded = [b for b in selected_benchmarks if b in benchmark_data]
            not_loaded = [b for b in selected_benchmarks if b not in benchmark_data]
            if loaded:
                st.caption(f"✅ 已加载: {', '.join(loaded)}")
            if not_loaded:
                st.caption(f"⚠️ 无法获取: {', '.join(not_loaded)}")
            
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
            # Absolute value view
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
        
        # Common layout
        has_benchmarks = len(selected_benchmarks) > 0
        chart_height = 500 if has_benchmarks else 420
        
        fig_history.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=chart_height,
            margin=dict(l=20, r=20, t=70, b=80 if has_benchmarks else 20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False,
                linecolor='#E5E7EB',
                tickfont=dict(size=11, color='#6B7280', family='Inter'),
                tickformat='%m/%d',
            ),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Inter',
                bordercolor='#E5E7EB'
            ),
            showlegend=has_benchmarks,
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.18,
                xanchor='center',
                x=0.5,
                font=dict(size=9, family='Inter'),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#E5E7EB',
                borderwidth=1
            )
        )
        
        st.plotly_chart(fig_history, use_container_width=True, config={'displayModeBar': False})
        
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
    
    elif len(history_df) == 1:
        st.info(L.CHART_NEED_2)
    else:
        st.info(L.CHART_NO_HISTORY)
    
    st.markdown("---")
    
    # Monthly Returns Heatmap
    st.subheader("📅 月度收益热力图")
    
    if not history_df.empty and len(history_df) > 1:
        history_df_temp = history_df.copy()
        history_df_temp['date'] = pd.to_datetime(history_df_temp['date'])
        history_df_temp = history_df_temp.sort_values('date')
        
        history_df_temp['year'] = history_df_temp['date'].dt.year
        history_df_temp['month'] = history_df_temp['date'].dt.month
        
        monthly_data = []
        for (year, month), group in history_df_temp.groupby(['year', 'month']):
            first_val = group['net_worth'].iloc[0]
            last_val = group['net_worth'].iloc[-1]
            change = last_val - first_val  # 具体金额变化
            ret = ((change) / first_val * 100) if first_val > 0 else 0
            monthly_data.append({'year': year, 'month': month, 'return': ret, 'change': change})
        
        monthly_df = pd.DataFrame(monthly_data)
        
        if not monthly_df.empty:
            months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
            
            # 收益率 pivot
            pivot = monthly_df.pivot(index='year', columns='month', values='return')
            pivot = pivot.reindex(columns=range(1, 13), fill_value=None)
            pivot.columns = months
            
            # 金额变化 pivot
            pivot_change = monthly_df.pivot(index='year', columns='month', values='change')
            pivot_change = pivot_change.reindex(columns=range(1, 13), fill_value=None)
            pivot_change.columns = months
            
            # 生成年份列表（确保是字符串格式）
            year_labels = [str(int(y)) for y in pivot.index.tolist()]
            
            # 计算年度汇总
            yearly_summary = monthly_df.groupby('year').agg({
                'return': 'sum',
                'change': 'sum'
            }).reset_index()
            
            # 添加年度汇总列
            months_with_total = months + ['年度']
            pivot['年度'] = [yearly_summary[yearly_summary['year'] == int(y)]['return'].values[0] 
                            if int(y) in yearly_summary['year'].values else None 
                            for y in year_labels]
            pivot_change['年度'] = [yearly_summary[yearly_summary['year'] == int(y)]['change'].values[0] 
                                   if int(y) in yearly_summary['year'].values else None 
                                   for y in year_labels]
            
            # 格子内只显示收益率百分比
            text_matrix = [[f"{v:+.1f}%" if pd.notna(v) else "" for v in row] for row in pivot.values]
            
            # 构建自定义 hover 文本（包含详细金额信息）
            hover_matrix = []
            for i, row in enumerate(pivot.values):
                hover_row = []
                for j, v in enumerate(row):
                    change_v = pivot_change.values[i][j] if j < len(pivot_change.values[i]) else None
                    year = year_labels[i]
                    col_name = months_with_total[j]
                    if pd.notna(v) and pd.notna(change_v):
                        change_display = change_v * fx_rate
                        if abs(change_display) >= 10000:
                            change_str = f"{change_display/1000:+,.1f}k"
                        elif abs(change_display) >= 1000:
                            change_str = f"{change_display:+,.0f}"
                        else:
                            change_str = f"{change_display:+.0f}"
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
                    [0, '#DC2626'],      # 深红 - 大亏
                    [0.35, '#FCA5A5'],   # 浅红 - 小亏
                    [0.5, '#F3F4F6'],    # 灰白 - 持平
                    [0.65, '#6EE7B7'],   # 浅绿 - 小赚
                    [1, '#059669']       # 深绿 - 大赚
                ],
                zmid=0,
                text=text_matrix,
                texttemplate="%{text}",
                textfont={"size": 13, "family": "Outfit", "color": "#1F2937"},
                hovertext=hover_matrix,
                hovertemplate="%{hovertext}<extra></extra>",
                showscale=True,
                xgap=3,  # 格子间距
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
                height=120 + len(pivot) * 70,  # 增加单元格高度
                margin=dict(l=60, r=100, t=50, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    side='top',
                    tickfont=dict(size=12, color='#374151', family='Inter'),
                    tickangle=0
                ),
                yaxis=dict(
                    tickfont=dict(size=14, color='#1F2937', family='Outfit', weight=600),
                    autorange='reversed',
                    type='category',
                    tickmode='array',
                    tickvals=year_labels,
                    ticktext=year_labels
                )
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True, config={'displayModeBar': False})
            
            # ========== 月收益柱状图 ==========
            st.markdown("##### 📊 月度收益趋势")
            
            monthly_df_sorted = monthly_df.sort_values(['year', 'month'])
            monthly_df_sorted['date_label'] = monthly_df_sorted.apply(
                lambda x: f"{int(x['year'])}/{int(x['month']):02d}", axis=1
            )
            
            bar_colors = ['#10B981' if r >= 0 else '#EF4444' for r in monthly_df_sorted['return']]
            
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=monthly_df_sorted['date_label'],
                y=monthly_df_sorted['return'],
                marker_color=bar_colors,
                text=[f"{r:+.1f}%" for r in monthly_df_sorted['return']],
                textposition='outside',
                textfont=dict(size=10, family='Outfit'),
                hovertemplate="<b>%{x}</b><br>收益率: %{y:+.2f}%<extra></extra>"
            ))
            
            fig_bar.update_layout(
                height=260,
                margin=dict(l=20, r=20, t=20, b=50),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    tickfont=dict(size=10, color='#6B7280', family='Inter'),
                    tickangle=-45,
                    showgrid=False
                ),
                yaxis=dict(
                    ticksuffix="%",
                    tickfont=dict(size=10, color='#6B7280'),
                    showgrid=True,
                    gridcolor='rgba(229, 231, 235, 0.5)',
                    griddash='dot',
                    zeroline=True,
                    zerolinecolor='#9CA3AF',
                    zerolinewidth=1
                ),
                showlegend=False,
                bargap=0.3
            )
            
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
            
            # ========== 美化统计卡片 ==========
            positive_months = (monthly_df['return'] > 0).sum()
            negative_months = (monthly_df['return'] < 0).sum()
            total_months = len(monthly_df)
            avg_return = monthly_df['return'].mean()
            avg_change = monthly_df['change'].mean() * fx_rate
            total_change = monthly_df['change'].sum() * fx_rate
            best_month = monthly_df.loc[monthly_df['return'].idxmax()]
            worst_month = monthly_df.loc[monthly_df['return'].idxmin()]
            
            def format_change(val):
                if abs(val) >= 10000:
                    return f"{val/1000:+,.1f}k"
                elif abs(val) >= 1000:
                    return f"{val:+,.0f}"
                else:
                    return f"{val:+.0f}"
            
            best_change = best_month['change'] * fx_rate
            worst_change = worst_month['change'] * fx_rate
            win_rate = positive_months / total_months * 100 if total_months > 0 else 0
            total_color = '#10B981' if total_change >= 0 else '#EF4444'
            
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 1.5rem 0;">
                <div class="u-card" style="padding: 20px; text-align: center; background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%); border: 1px solid #86EFAC;">
                    <div style="font-size: 0.75rem; color: #15803D; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">平均月收益</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #166534; font-family: Outfit; margin: 8px 0;">{avg_return:+.2f}%</div>
                    <div style="font-size: 0.8rem; color: #22C55E;">{cur_sym}{format_change(avg_change)}/月</div>
                </div>
                <div class="u-card" style="padding: 20px; text-align: center; background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1px solid #93C5FD;">
                    <div style="font-size: 0.75rem; color: #1D4ED8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">盈利月份</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #1E40AF; font-family: Outfit; margin: 8px 0;">{positive_months}/{total_months}</div>
                    <div style="font-size: 0.8rem; color: #3B82F6;">胜率 {win_rate:.0f}%</div>
                </div>
                <div class="u-card" style="padding: 20px; text-align: center; background: linear-gradient(135deg, #F0FDF4 0%, #D1FAE5 100%); border: 1px solid #6EE7B7;">
                    <div style="font-size: 0.75rem; color: #047857; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">🏆 最佳月份</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #065F46; font-family: Outfit; margin: 8px 0;">{int(best_month['year'])}/{int(best_month['month']):02d}</div>
                    <div style="font-size: 0.85rem; color: #10B981; font-weight: 600;">+{best_month['return']:.2f}% ({cur_sym}{format_change(best_change)})</div>
                </div>
                <div class="u-card" style="padding: 20px; text-align: center; background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%); border: 1px solid #FCA5A5;">
                    <div style="font-size: 0.75rem; color: #B91C1C; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">📉 最差月份</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #991B1B; font-family: Outfit; margin: 8px 0;">{int(worst_month['year'])}/{int(worst_month['month']):02d}</div>
                    <div style="font-size: 0.85rem; color: #EF4444; font-weight: 600;">{worst_month['return']:.2f}% ({cur_sym}{format_change(worst_change)})</div>
                </div>
            </div>
            
            <div class="u-card" style="padding: 16px 24px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(90deg, #F8FAFC 0%, #F1F5F9 100%);">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.5rem;">💰</span>
                    <div>
                        <div style="font-size: 0.75rem; color: #64748B; text-transform: uppercase;">累计总收益</div>
                        <div style="font-size: 1.3rem; font-weight: 700; color: {total_color}; font-family: Outfit;">{cur_sym}{format_change(total_change)}</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.75rem; color: #64748B;">统计周期</div>
                    <div style="font-size: 0.9rem; font-weight: 600; color: #334155;">{total_months} 个月</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("需要至少2个月的数据才能显示热力图")
    
    st.markdown("---")
    
    # Holdings detail
    st.subheader(L.HOLDINGS_DETAIL)
    
    if not net_worth_data['details'].empty:
        details_display = net_worth_data['details'].copy()
        details_display['quantity'] = details_display['quantity'].apply(lambda x: f"{x:,.8f}".rstrip('0').rstrip('.'))
        details_display['price'] = details_display['price'].apply(lambda x: f"{cur_sym}{x * fx_rate:,.2f}")
        details_display['value'] = details_display['value'].apply(lambda x: f"{cur_sym}{x * fx_rate:,.2f}")
        details_display = details_display[['account_name', 'symbol', 'quantity', 'price', 'value']]
        details_display.columns = [L.HOLDINGS_ACCOUNT, L.HOLDINGS_ASSET, L.HOLDINGS_QTY, L.HOLDINGS_PRICE, L.HOLDINGS_VALUE]
        
        st.dataframe(details_display, use_container_width=True, hide_index=True)
    else:
        st.info(L.HOLDINGS_NO_DATA)
