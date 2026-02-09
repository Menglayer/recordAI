"""
Dashboard page - Main overview with charts and metrics
重构后的模块化入口，保持向后兼容

注意：此文件现在是一个转发入口，实际实现已拆分到 pages/dashboard/ 目录下：
- metrics.py: 指标卡片组件
- time_returns.py: 时间收益率组件
- charts.py: 图表渲染组件
- holdings.py: 持仓表格组件
- main.py: 主入口整合
"""

# 从新的模块化结构导入 show_dashboard
from pages.dashboard.main import show_dashboard

# 导出 show_dashboard 保持向后兼容
__all__ = ['show_dashboard']
