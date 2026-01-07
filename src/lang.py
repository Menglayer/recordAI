# -*- coding: utf-8 -*-
"""
Language strings for MyLedger (Chinese)
"""

# App
APP_TITLE = "MyLedger - 个人资产追踪工具"
APP_SUBTITLE = "追踪资产，分析投资收益"

# Navigation
NAV_DASHBOARD = "仪表盘"
NAV_DATA_ENTRY = "数据录入"
NAV_PRICE_UPDATE = "价格更新"
NAV_DATA_VIEW = "数据查看"
NAV_TIPS = "使用提示"

# Sidebar
SIDEBAR_NAV = "导航"
SIDEBAR_STATS = "数据统计"
STAT_SNAPSHOTS = "快照记录"
STAT_TRANSFERS = "转账记录"
STAT_PRICES = "价格记录"

# Dashboard
DASH_NO_DATA = "暂无快照数据，请先在数据录入页面添加快照"
DASH_DATA_DATE = "数据日期"
DASH_BASED_ON = "基于最新快照"
DASH_NET_WORTH = "总净值"
DASH_INVESTED = "总投入"
DASH_PNL = "未实现盈亏"
DASH_ROI = "收益率"
DASH_PROFIT = "盈利"
DASH_LOSS = "亏损"
DASH_EVEN = "持平"
DASH_IN = "入金"
DASH_OUT = "出金"
DASH_NET_INV_HELP = "净投入 = 入金 - 出金"
DASH_NW_HELP = "所有资产总价值"
DASH_PNL_HELP = "净值 - 净投入"

# Time returns
TIME_RETURNS = "时间收益分析"
TIME_PERIOD = "分析区间"
TIME_START = "起始"
TIME_END = "结束"
TIME_DAYS = "天数"
TIME_HOURS = "小时"
TIME_NW_CHANGE = "净值变化"
TIME_CHANGE = "变化"
TIME_CASH_FLOW = "现金流"
TIME_DEPOSITS = "入金"
TIME_WITHDRAWALS = "出金"
TIME_NET = "净流入"
TIME_PERIOD_ROI = "期间 ROI"
TIME_APY = "年化收益率 APY"
TIME_ANNUALIZED = "年化"
TIME_HIGH_VOL = "高波动"

# Charts
CHART_ASSET_DIST = "资产分布"
CHART_ACCOUNT_DIST = "账户分布"
CHART_BY_ASSET = "按资产"
CHART_BY_ACCOUNT = "按账户"
CHART_NO_DATA = "暂无数据"
CHART_MISSING_PRICE = "部分资产缺少价格数据，请更新价格"
CHART_HISTORY = "净值历史"
CHART_NW_OVER_TIME = "净值走势"
CHART_DATE = "日期"
CHART_NW_USD = "净值 (USD)"
CHART_ATH = "历史最高"
CHART_ATL = "历史最低"
CHART_GROWTH = "总增长"
CHART_NEED_2 = "至少需要2个快照才能显示历史"
CHART_NO_HISTORY = "暂无历史数据"

# Holdings
HOLDINGS_DETAIL = "持仓明细"
HOLDINGS_ACCOUNT = "账户"
HOLDINGS_ASSET = "资产"
HOLDINGS_QTY = "数量"
HOLDINGS_PRICE = "单价"
HOLDINGS_VALUE = "价值"
HOLDINGS_NO_DATA = "暂无持仓数据"

# Data Entry
ENTRY_TITLE = "数据录入"
ENTRY_SNAPSHOT = "资产快照"
ENTRY_TRANSFER = "资金转账"
ENTRY_SETTINGS = "设置"
ENTRY_DATE = "日期"
ENTRY_SNAPSHOT_DATE = "快照日期"
ENTRY_SELECT_EXISTING = "选择已有"
ENTRY_NEW_ACCOUNT = "新建账户"
ENTRY_ACCOUNT = "账户"
ENTRY_ACCOUNT_NAME = "账户名称"
ENTRY_ACCOUNT_HINT = "如: Binance, OKX"
ENTRY_CURRENT_ACCOUNT = "当前账户"
ENTRY_NONE = "(未选择)"
ENTRY_HOLDINGS = "持仓信息"
ENTRY_SYMBOL = "资产代码"
ENTRY_SYMBOL_HINT = "如: BTC, ETH"
ENTRY_QUANTITY = "数量"
ENTRY_QTY_HELP = "持仓数量"
ENTRY_VALID_ROWS = "有效记录"
ENTRY_SAVE_SNAPSHOT = "保存快照"
ENTRY_CLEAR = "清空"
ENTRY_ENTER_ACCOUNT = "请输入账户名称"
ENTRY_NO_VALID = "没有有效记录可保存"
ENTRY_SAVED_N = "已保存 {} 条快照记录!"
ENTRY_SAVE_FAILED = "保存失败"

# Transfer
TRANSFER_TITLE = "资金转账 (入金/出金)"
TRANSFER_TYPE = "类型"
TRANSFER_DEPOSIT = "入金"
TRANSFER_WITHDRAWAL = "出金"
TRANSFER_AMOUNT = "金额 (USD)"
TRANSFER_NOTE = "备注"
TRANSFER_OPTIONAL = "可选"
TRANSFER_SAVE = "保存转账"
TRANSFER_AMOUNT_GT0 = "金额必须大于 0"
TRANSFER_SAVED = "已保存 {} ${:,.2f}"

# Price
PRICE_TITLE = "价格更新"
PRICE_AUTO = "自动获取"
PRICE_MANUAL = "手动输入"
PRICE_NO_SNAPSHOTS = "没有快照记录，请先添加快照"
PRICE_FOUND_N = "找到 {} 个资产: {}"
PRICE_SOURCE = "来源"
PRICE_FROM_SNAPSHOTS = "从快照获取"
PRICE_CUSTOM = "自定义输入"
PRICE_WILL_FETCH = "将获取 {} 个资产"
PRICE_SYMBOLS_HINT = "每行输入一个代码"
PRICE_FETCH = "获取价格"
PRICE_NO_SYMBOLS = "没有要获取的资产"
PRICE_FETCHING = "正在获取 {} 个资产的价格..."
PRICE_UPDATED_N = "已更新 {} 个价格!"
PRICE_FETCH_FAILED = "获取失败"
PRICE_SYMBOL = "代码"
PRICE_PRICE = "价格 (USD)"
PRICE_SAVE = "保存价格"
PRICE_ENTER_SYMBOL = "请输入代码"
PRICE_GT0 = "价格必须大于 0"
PRICE_SAVED = "已保存 {} 价格: ${:,.4f}"
PRICE_SAVE_FAILED = "保存失败"

# Data View
VIEW_TITLE = "数据查看"
VIEW_SNAPSHOTS = "快照"
VIEW_TRANSFERS = "转账"
VIEW_PRICES = "价格"
VIEW_RECENT = "最近记录"
VIEW_NO_DATA = "暂无数据"
VIEW_SOURCE = "来源"

# Tips
TIPS_TITLE = "使用提示"
TIPS_CONTENT = """
### 资产快照

1. **选择日期和账户**: 选择快照日期，选择或输入账户名称
2. **编辑持仓表格**: 
   - 点击单元格编辑
   - 使用 + 按钮添加行
   - 代码会自动转为大写
3. **保存快照**: 点击保存按钮

**提示**: 相同日期/账户/资产会更新现有记录

---

### 资金转账

1. **选择日期和类型**: 
   - 入金: 资金转入
   - 出金: 资金转出
2. **输入金额**: 以美元为单位
3. **添加备注**: 可选描述
4. **保存**: 点击保存按钮

**用途**: 区分投资收益和新增资金

---

### 最佳实践

- 定期记录快照 (每天/每周)
- 使用统一的账户命名
- 及时记录所有转账
- 添加快照后更新价格

---

### 下一步

完成录入后:
- 使用价格更新获取资产价格
- 查看仪表盘进行分析
- 按需导出数据
"""
