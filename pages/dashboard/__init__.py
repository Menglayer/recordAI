"""
Dashboard module
拆分的 Dashboard 组件集合
"""
from pages.dashboard.metrics import render_net_worth_card, render_goal_progress, render_summary_metrics
from pages.dashboard.time_returns import render_time_returns_section
from pages.dashboard.charts import render_asset_charts, render_history_chart, render_monthly_heatmap
from pages.dashboard.holdings import render_holdings_table
from pages.dashboard.main import show_dashboard

__all__ = [
    'show_dashboard',
    'render_net_worth_card',
    'render_goal_progress', 
    'render_summary_metrics',
    'render_time_returns_section',
    'render_asset_charts',
    'render_history_chart',
    'render_monthly_heatmap',
    'render_holdings_table'
]
