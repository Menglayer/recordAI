# -*- coding: utf-8 -*-
"""
MyLedger - 全局配置常量
集中管理散布在各模块中的硬编码值
"""

# ========== 业务默认值 ==========
DEFAULT_NET_WORTH_GOAL = 500_000       # 默认目标净值 (USD)
DEFAULT_BTC_PRICE_FALLBACK = 100_000.0  # BTC 价格最终 fallback 值
MIN_DISPLAY_VALUE = 10                  # 小额过滤阈值 (USD)，低于此值不显示

# ========== 缓存配置 (秒) ==========
CACHE_TTL_SHORT = 60          # 短缓存：快照、转账、账户列表等频繁变动数据
CACHE_TTL_MEDIUM = 300        # 中缓存：价格数据、BTC 实时价格
CACHE_TTL_LONG = 3600         # 长缓存：汇率等稳定数据

# ========== 数据库 ==========
SESSION_FACTORY_CACHE_SIZE = 4   # sessionmaker 工厂缓存大小
DB_POOL_SIZE = 5                 # 连接池大小
DB_MAX_OVERFLOW = 10             # 连接池最大溢出
DB_POOL_RECYCLE = 300            # 连接回收时间 (秒)
DB_CONNECT_TIMEOUT = 30          # 连接超时 (秒)

# ========== 货币 ==========
SUPPORTED_CURRENCIES = ["USD", "CNY", "EUR", "GBP", "JPY", "HKD", "AUD"]
CURRENCY_SYMBOLS = {
    "USD": "$",
    "CNY": "¥",
    "EUR": "€",
    "JPY": "¥",
    "GBP": "£",
    "HKD": "HK$",
    "AUD": "A$",
}
