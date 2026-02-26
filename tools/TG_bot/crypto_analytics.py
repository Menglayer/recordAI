"""
加密货币技术分析与策略模块
Ahr999、MA均线、RSI、布林带、Sell Put/Call 策略等
"""
import math
import statistics
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ================= 常量 =================
GENESIS_DATE = datetime(2009, 1, 3, tzinfo=timezone.utc)


# ================= 纯数学工具 =================

def calculate_std(data, ddof=0):
    """
    计算标准差
    
    Args:
        data: 数据列表
        ddof: 自由度
        
    Returns:
        float: 标准差
    """
    n = len(data)
    if n < 2:
        return 0.0
    mean_val = sum(data) / n
    ss = sum((x - mean_val) ** 2 for x in data)
    return math.sqrt(ss / (n - ddof))


def norm_ppf(p):
    """标准正态分布分位点函数 (Inverse CDF)"""
    try:
        return statistics.NormalDist().inv_cdf(p)
    except Exception:
        return 0.0


# ================= 技术指标 =================

def calculate_ahr999(price):
    """
    计算 Ahr999 囤币指标的拟合价格

    Args:
        price: 当前价格（未直接使用，但保留接口兼容）
        
    Returns:
        float: 拟合价格
    """
    age_days = (datetime.now(timezone.utc) - GENESIS_DATE).days
    log_age = math.log10(age_days)
    fit_price = 10 ** (5.84 * log_age - 17.01)
    return fit_price


def calculate_analytics(closes):
    """
    计算技术指标集合
    
    Args:
        closes: 收盘价列表
        
    Returns:
        dict: 包含 ma120, ma200, ma730, ahr999, hv, ma20, bb_up, bb_low, rsi
    """
    if not closes:
        return {}
    n = len(closes)
    price = closes[-1]

    # 均线
    ma120 = sum(closes[-120:]) / 120.0 if n >= 120 else price
    ma200 = sum(closes[-200:]) / 200.0 if n >= 200 else price
    ma730 = sum(closes[-730:]) / 730.0 if n >= 730 else price

    # Ahr999
    fit_price = calculate_ahr999(price)
    ahr999 = (price / ma200) * (price / fit_price)

    # 历史波动率 (HV)
    log_rets = []
    for i in range(1, n):
        if closes[i - 1] > 0:
            log_rets.append(math.log(closes[i] / closes[i - 1]))

    recent_rets = log_rets[-30:] if len(log_rets) >= 30 else log_rets
    if recent_rets:
        std_dev = calculate_std(recent_rets, ddof=0)
        hv = std_dev * math.sqrt(365)
    else:
        hv = 0.5

    # 布林带 (MA20, 2σ)
    recent_20 = closes[-20:]
    if len(recent_20) == 20:
        ma20 = sum(recent_20) / 20.0
        std20 = calculate_std(recent_20, ddof=0)
        bb_up = ma20 + 2 * std20
        bb_low = ma20 - 2 * std20
    else:
        ma20, bb_up, bb_low = price, price, price

    # RSI (14)
    gains, losses = [], []
    sub_closes = closes[-15:]
    for i in range(1, len(sub_closes)):
        delta = sub_closes[i] - sub_closes[i - 1]
        if delta > 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))

    if gains:
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        if avg_loss == 0 and avg_gain == 0:
            rsi = 50.0  # 价格无变化，RSI 中性
        elif avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
    else:
        rsi = 50.0

    return {
        'ma120': ma120, 'ma200': ma200, 'ma730': ma730,
        'ahr999': ahr999, 'hv': hv, 'ma20': ma20,
        'bb_up': bb_up, 'bb_low': bb_low, 'rsi': rsi
    }


# ================= Sell Put 策略 (买入端) =================

def get_risk_zone(r):
    """
    根据 price / MA120 比值决定风险区间
    
    Returns:
        tuple: (区间名称, 仓位比例, delta, 到期天数, 操作描述)
    """
    if r < 0.60:
        return "🌌 史诗底", 1.0, 0.30, 30, "全仓进攻"
    if r < 0.80:
        return "🩸 深熊区", 0.85, 0.25, 28, "主力吸筹"
    if r < 0.95:
        return "📉 低估区", 0.70, 0.20, 21, "适度建仓"
    if r <= 1.05:
        return "⚖️ 震荡区", 0.40, 0.15, 14, "防守收租"
    return "🛡️ 高估区", 0.20, 0.08, 7, "暂停/远虚"


def estimate_strike(S, delta, days, sigma):
    """
    估算 Put 期权行权价
    
    Args:
        S: 标的价格
        delta: Put Delta
        days: 到期天数
        sigma: 隐含波动率
        
    Returns:
        float: 行权价
    """
    T = days / 365.0
    r = 0.04
    val_ppf = norm_ppf(delta)
    d1 = -val_ppf
    return S / math.exp(d1 * sigma * math.sqrt(T) - (r + 0.5 * sigma ** 2) * T)


# ================= Sell Call 策略 (卖出端) =================

def get_call_zone(r):
    """
    MA120 天空五档
    
    Returns:
        tuple: (区间名称, delta, 到期天数, 操作描述)
    """
    if r < 0.95:
        return "🌑 潜伏区", 0.0, 0, "拿住装死 (不卖)"
    if r < 1.10:
        return "🌤️ 震荡区", 0.10, 7, "摸奖/远虚"
    if r < 1.30:
        return "🚀 加速区", 0.20, 14, "保守收租"
    if r < 1.50:
        return "🔥 狂热区", 0.30, 21, "积极收租"
    return "🪐 宇宙顶", 0.45, 30, "清仓/深实值"


def estimate_call_strike(S, delta, days, sigma):
    """
    反推 Call 行权价 (K > S)
    
    Args:
        S: 标的价格
        delta: Call Delta
        days: 到期天数
        sigma: 隐含波动率
        
    Returns:
        float: 行权价
    """
    T = days / 365.0
    r = 0.04
    d1 = norm_ppf(delta)
    return S / math.exp(d1 * sigma * math.sqrt(T) - (r + 0.5 * sigma ** 2) * T)
