import os
import asyncio
import logging
import requests
import time
import base64
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

# RSA 签名依赖
from cryptography.hazmat.primitives import serialization
# from scipy.stats import norm (Removed)

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import math
import statistics

# 🆕 MyLedger 集成
try:
    from ledger_commands import register_ledger_handlers
    LEDGER_ENABLED = True
except ImportError:
    LEDGER_ENABLED = False

# ================= 配置区域 =================
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN', '').strip()
TG_CHAT_ID_ENV = os.environ.get('TG_CHAT_ID', '').strip()
MY_SECRET_TOKEN = os.environ.get('MY_SECRET_TOKEN', '').strip()

# RSA 认证配置
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY', '').strip()
PRIVATE_KEY_B64 = os.environ.get('PRIVATE_KEY_BASE64', '').strip()

# 核心策略参数
TARGET_BTC_CAP = 3.0            
DAILY_DCA_AMOUNT = 500.0        
DCA_DAYS_PREDICTION = 30        

# 模拟基准
DCA_START_DATE = "2025-12-04"
INITIAL_SPOT_HOLDINGS = 0.04168

# 固定配置
BASE_URL_SPOT = 'https://api.binance.com'
BASE_URL_FUTURES = 'https://fapi.binance.com'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

_session = requests.Session()
_application = None

# ================= 1. RSA 签名核心逻辑 (不变) =================

def load_private_key():
    try:
        if not PRIVATE_KEY_B64: return None
        clean_key = PRIVATE_KEY_B64.replace('\\n', '\n').strip()
        key_bytes = base64.b64decode(clean_key)
        return serialization.load_pem_private_key(key_bytes, password=None)
    except Exception as e:
        logger.error(f"Private Key Load Error: {e}")
        return None

def send_signed_request(method, endpoint, params=None):
    if not BINANCE_API_KEY or not PRIVATE_KEY_B64: return None
    if params is None: params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 60000 
    query_string = urlencode(params)
    private_key = load_private_key()
    if not private_key: return None
    try:
        signature = base64.b64encode(
            private_key.sign(query_string.encode('utf-8'))
        ).decode('utf-8')
    except Exception as e:
        logger.error(f"Signing Error: {e}")
        return None
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    url = f"{BASE_URL_SPOT}{endpoint}"
    try:
        full_params = params.copy()
        full_params['signature'] = signature
        if method.upper() == 'GET':
            response = _session.get(url, params=full_params, headers=headers, timeout=10)
        else:
            response = _session.post(url, data=full_params, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Network Error: {e}")
        return None

# ================= 2. 数据计算工具 =================

GENESIS_DATE = datetime(2009, 1, 3, tzinfo=timezone.utc)

def get_earn_apr(asset='BTC'):
    """获取理财产品实时 APR (用于估算)"""
    try:
        # 获取 Simple Earn Flexible 列表
        res = send_signed_request('GET', '/sapi/v1/simple-earn/flexible/list', {'asset': asset, 'current': 1, 'size': 5})
        if res and 'rows' in res and res['rows']:
            # 取第一个产品的 APR (通常是 Tier 1 或最新)
            return float(res['rows'][0]['latestAnnualPercentageRate'])
    except Exception as e:
        logger.error(f"APR Fetch Error: {e}")
    return 0.0

def get_real_total_balance():
    """获取 [现货 + 理财] 总余额"""
    if not BINANCE_API_KEY: return None
    spot_btc, spot_usdt = 0.0, 0.0
    s_res = send_signed_request('GET', '/api/v3/account')
    if s_res and 'balances' in s_res:
        for b in s_res['balances']:
            if b['asset'] == 'BTC': spot_btc = float(b['free']) + float(b['locked'])
            if b['asset'] == 'USDT': spot_usdt = float(b['free']) + float(b['locked'])

    earn_btc, earn_usdt = 0.0, 0.0
    for path in ['/sapi/v1/simple-earn/flexible/position', '/sapi/v1/simple-earn/locked/position']:
        res = send_signed_request('GET', path, {'limit': 100})
        items = []
        if isinstance(res, dict) and 'rows' in res: items = res['rows']
        elif isinstance(res, list): items = res
        for row in items:
            if row['asset'] == 'BTC': earn_btc += float(row['totalAmount'])
            if row['asset'] == 'USDT': earn_usdt += float(row['totalAmount'])

    return spot_btc + earn_btc, spot_usdt + earn_usdt, {
        'spot_btc': spot_btc, 'earn_btc': earn_btc,
        'spot_usdt': spot_usdt, 'earn_usdt': earn_usdt
    }

def get_fng_index():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=3)
        data = r.json()
        return int(data['data'][0]['value']), data['data'][0]['value_classification']
    except:
        return 50, "Unknown"

# --- 纯 Python 统计函数 ---
def calculate_std(data, ddof=0):
    """计算标准差 (默认总体标准差 ddof=0，与 numpy一致)"""
    n = len(data)
    if n < 2: return 0.0
    mean_val = sum(data) / n
    ss = sum((x - mean_val) ** 2 for x in data)
    return math.sqrt(ss / (n - ddof))

def calculate_ahr999(price):
    """计算 Ahr999 囤币指标"""
    # 1. 币龄
    age_days = (datetime.now(timezone.utc) - GENESIS_DATE).days
    
    # 2. 几何平均价格 (估值) = 10^(5.84 * log10(days) - 17.01)
    # Ahr999 拟合公式
    log_age = math.log10(age_days)
    fit_price = 10 ** (5.84 * log_age - 17.01)
    
    return fit_price

def calculate_analytics(closes):
    """计算技术指标 (去 numpy 版)"""
    # 需要足够的 K 线数据
    if not closes: return {}
    n = len(closes)
    
    # 基础数据
    price = closes[-1]
    
    # MA120 (用于深海策略)
    ma120 = sum(closes[-120:]) / 120.0 if n >= 120 else price
    
    # MA200 (用于 Ahr999 成本部分)
    ma200 = sum(closes[-200:]) / 200.0 if n >= 200 else price

    # MA730 (两年线 / 逃顶指标)
    ma730 = sum(closes[-730:]) / 730.0 if n >= 730 else price
    
    # Ahr999 计算
    fit_price = calculate_ahr999(price)
    ahr999 = (price / ma200) * (price / fit_price)
    
    # RV (Historical Volatility)
    # log_rets = ln(p[i]/p[i-1])
    log_rets = []
    for i in range(1, n):
        if closes[i-1] > 0:
            log_rets.append(math.log(closes[i] / closes[i-1]))
    
    # 取最近 30 天的 log returns
    recent_rets = log_rets[-30:] if len(log_rets) >= 30 else log_rets
    if recent_rets:
        # ⚠️ numpy.std 默认是 ddof=0 (总体标准差), statistics.stdev 是 sample (ddof=1)
        # 这里手写一个 ddof=0 的 std 以保持一致
        std_dev = calculate_std(recent_rets, ddof=0)
        hv = std_dev * math.sqrt(365)
    else:
        hv = 0.5 # fallback

    # 布林带 (MA20, 2std)
    recent_20 = closes[-20:]
    if len(recent_20) == 20:
        ma20 = sum(recent_20) / 20.0
        std20 = calculate_std(recent_20, ddof=0)
        bb_up = ma20 + 2 * std20
        bb_low = ma20 - 2 * std20
    else:
        ma20, bb_up, bb_low = price, price, price

    # RSI (14)
    # diffs
    gains = []
    losses = []
    # 只需要取最后 15 个点来计算最近 14 个 change 
    # (或者取更多平滑，这里简化逻辑仿照原版)
    sub_closes = closes[-15:] 
    for i in range(1, len(sub_closes)):
        delta = sub_closes[i] - sub_closes[i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))
    
    if gains:
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        if avg_loss == 0:
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

# --- 策略核心：Sell Put (买入端) ---
def get_risk_zone(r):
    if r < 0.60: return "🌌 史诗底", 1.0, 0.30, 30, "全仓进攻"
    if r < 0.80: return "🩸 深熊区", 0.85, 0.25, 28, "主力吸筹"
    if r < 0.95: return "📉 低估区", 0.70, 0.20, 21, "适度建仓"
    if r <= 1.05: return "⚖️ 震荡区", 0.40, 0.15, 14, "防守收租"
    return "🛡️ 高估区", 0.20, 0.08, 7, "暂停/远虚"   

def norm_ppf(p):
    """标准正态分布分位点函数 (Inverse CDF)"""
    # Python 3.8+ 提供了 statistics.NormalDist
    try:
        return statistics.NormalDist().inv_cdf(p)
    except:
        #均值0 标准差1
        return 0.0 # Fallback mainly for very old python, mostly won't hit

def estimate_strike(S, delta, days, sigma):
    T = days / 365.0
    r = 0.04
    # d1 = -norm.ppf(delta) => norm.ppf(delta) is negative for delta < 0.5 usually?
    # Wait, Put Delta is usually negative or interpreted as abs logic.
    # In original code: d1 = -norm.ppf(delta). 
    # Usually Put Delta = N(d1) - 1. Or using N(-d1).
    # If user inputs delta positive (e.g. 0.30), norm.ppf(0.30) is negative (approx -0.52).
    # so d1 = -(-0.52) = +0.52.
    # This logic seems specific to user's formula. We keep it AS IS.
    
    val_ppf = norm_ppf(delta)
    d1 = -val_ppf
    
    # K = S / exp(...)
    return S / math.exp(d1 * sigma * math.sqrt(T) - (r + 0.5 * sigma**2) * T)

# --- 🔥 新增策略核心：Sell Call (卖出端) ---
def get_call_zone(r):
    """MA120 天空五档"""
    if r < 0.95: return "🌑 潜伏区", 0.0, 0, "拿住装死 (不卖)"
    if r < 1.10: return "🌤️ 震荡区", 0.10, 7, "摸奖/远虚"
    if r < 1.30: return "🚀 加速区", 0.20, 14, "保守收租"
    if r < 1.50: return "🔥 狂热区", 0.30, 21, "积极收租"
    return "🪐 宇宙顶", 0.45, 30, "清仓/深实值"

def estimate_call_strike(S, delta, days, sigma):
    """反推 Call Strike (K > S)"""
    T = days / 365.0
    r = 0.04
    # Call Delta = N(d1)
    d1 = norm_ppf(delta) 
    # K = S / exp(...)
    return S / math.exp(d1 * sigma * math.sqrt(T) - (r + 0.5 * sigma**2) * T)

# ================= 3. 指令逻辑 =================

ALLOWED_IDS = set()
if TG_CHAT_ID_ENV:
    ALLOWED_IDS = set(int(x.strip()) for x in TG_CHAT_ID_ENV.split(',') if x.strip())

async def check_auth(update: Update):
    if update.effective_user.id in ALLOWED_IDS: return True
    await update.message.reply_text("⛔️ Denied")
    return False

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    try:
        # 扩展 K 线获取至 800+ 以支持 MA730 (两年线)
        res = _session.get(f"{BASE_URL_SPOT}/api/v3/klines", params={'symbol':'BTCUSDT','interval':'1d','limit':800}, timeout=5).json()
        closes = [float(k[4]) for k in res]
        p = closes[-1]
        stats = calculate_analytics(closes)
        
        f_res = _session.get(f"{BASE_URL_FUTURES}/fapi/v1/premiumIndex?symbol=BTCUSDT", timeout=5).json()
        fund = float(f_res['lastFundingRate'])
        fng_val, fng_class = get_fng_index()
        t_res = _session.get(f"{BASE_URL_SPOT}/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=5).json()
        chg = float(t_res['priceChangePercent'])
        
        rsi = stats.get('rsi', 50)
        rsi_state = "🔥超买" if rsi > 70 else ("❄️超卖" if rsi < 30 else "😐中性")
        bb_up, bb_low = stats.get('bb_up', 0), stats.get('bb_low', 0)
        
        # Ahr999 状态
        ahr = stats.get('ahr999', 99)
        if ahr < 0.45: ahr_state = "� 抄底 (Buy)"
        elif ahr < 1.2: ahr_state = "� 定投 (Hold)"
        elif ahr < 5.0: ahr_state = "🚀 起飞 (Sit)"
        else: ahr_state = "🏃 逃顶 (Top)"

        # 两年线状态
        ma730 = stats.get('ma730', 0)
        ma730_top = ma730 * 5
        ma730_status = f"距离逃顶: {((ma730_top/p)-1)*100:+.1f}%" if ma730 > 0 else "N/A"
        if p > ma730_top: ma730_status = "⚠️ **已破两年线顶!**"

        msg = (
            f"📊 **BTC 市场全景 (Holder版)**\n"
            f"══════════════════\n"
            f"💵 **价格现况**\n"
            f"• 现价: `${p:,.0f}` ({chg:+.2f}%)\n"
            f"• MA120: `${stats['ma120']:,.0f}` (牛熊)\n"
            f"──────────────────\n"
            f"🟢 **囤币指标 (Ahr999)**\n"
            f"• 指数: `{ahr:.3f}`\n"
            f"• 状态: **{ahr_state}**\n"
            f"──────────────────\n"
            f"🔴 **逃顶指标 (2-Year)**\n"
            f"• 两年均线: `${ma730:,.0f}`\n"
            f"• 顶部上限: `${ma730_top:,.0f}`\n"
            f"• {ma730_status}\n"
            f"──────────────────\n"
            f"🧠 **情绪与压力**\n"
            f"• 恐慌指数: `{fng_val}` ({fng_class})\n"
            f"• 资金费率: `{fund*100:.4f}%`\n"
            f"• 波动率HV: `{stats['hv']*100:.1f}%`\n"
            f"──────────────────\n"
            f"📈 **技术指标**\n"
            f"• RSI(14): `{rsi:.1f}` {rsi_state}\n"
            f"• 布林带: \n"
            f"  ┠ `${bb_up:,.0f}` (上轨)\n"
            f"  ┠ `${stats['ma20']:,.0f}` (中轨)\n"
            f"  ┖ `${bb_low:,.0f}` (下轨)"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Market Error: {e}")
        await update.message.reply_text("❌ 数据获取失败")

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    msg = await update.message.reply_text("⏳ 由于是 Holder，正在用心审计...")
    def run_check():
        p_url = f"{BASE_URL_SPOT}/api/v3/ticker/price?symbol=BTCUSDT"
        price = float(_session.get(p_url, timeout=5).json()['price'])
        real_data = get_real_total_balance()
        if real_data:
            btc_tot, usdt_tot, d = real_data
            tag = "🟢 **实盘 (RSA)**"
        else:
            btc_tot = INITIAL_SPOT_HOLDINGS; usdt_tot = 0
            tag = "🟠 **模拟数据**"
            
        # 自由倒计时
        rem_btc = max(0.0, TARGET_BTC_CAP - btc_tot)
        rem_usdt = rem_btc * price
        
        # 假设每日定投
        days_to_finish = int(rem_usdt / DAILY_DCA_AMOUNT) if DAILY_DCA_AMOUNT > 0 else 9999
        finish_date = (datetime.now() + timedelta(days=days_to_finish)).strftime("%Y-%m")
        
        progress = (btc_tot / TARGET_BTC_CAP) * 100
        
        return (
            f"👛 **财富自由进度表**\n{tag}\n"
            f"══════════════════\n"
            f"📦 **核心资产**\n"
            f"• 总持仓: `{btc_tot:.4f} BTC`\n"
            f"• 市值: `${btc_tot*price:,.0f}`\n"
            f"──────────────────\n"
            f"🎯 **目标: {TARGET_BTC_CAP} BTC**\n"
            f"• 进度: `{progress:.2f}%`\n"
            f"• 剩余: `{rem_btc:.4f} BTC`\n"
            f"• 缺口: `${rem_usdt:,.0f}`\n"
            f"──────────────────\n"
            f"⏳ **倒计时 (按${DAILY_DCA_AMOUNT}/天)**\n"
            f"• 预计天数: `{days_to_finish} 天`\n"
            f"• 预计达成: `{finish_date}`"
        )
    report = await asyncio.to_thread(run_check)
    await msg.edit_text(report, parse_mode='Markdown')

# --- /sellput (买入端) ---
async def sellput_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    msg = await update.message.reply_text("⏳ 计算抄底策略...")

    def run_strat():
        try:
            res = _session.get(f"{BASE_URL_SPOT}/api/v3/klines", params={'symbol':'BTCUSDT','interval':'1d','limit':300}, timeout=10).json()
            closes = [float(k[4]) for k in res]
            stats = calculate_analytics(closes)
            if not stats: return "⚠️ K线不足"
            p, ma, hv = closes[-1], stats['ma120'], stats['hv']
            
            sigma = min(2.0, max(0.40, hv * 1.1))

            real_data = get_real_total_balance()
            btc_holdings = real_data[0] if real_data else INITIAL_SPOT_HOLDINGS
            
            con_price = min(p, ma) * 0.9
            future_dca = (DAILY_DCA_AMOUNT * DCA_DAYS_PREDICTION) / con_price
            total_risk = btc_holdings + future_dca
            rem = TARGET_BTC_CAP - total_risk
            
            zone, pct, delta, term, desc = get_risk_zone(p/ma)
            final_amt = max(0.0, min(rem, (TARGET_BTC_CAP * pct) - btc_holdings))
            
            raw_strike = estimate_strike(p, delta, term, sigma)
            safe_raw = min(raw_strike, p * 0.96)
            final_strike = round(safe_raw / 1000) * 1000
            if final_strike >= p: final_strike -= 1000
            
            date_str = (datetime.now(timezone.utc) + timedelta(days=term)).strftime("%m-%d")
            trade_txt = ""
            usdt = 0
            
            if final_amt > 0:
                if final_amt >= 0.2:
                    a, b = round(final_amt*0.6, 3), round(final_amt*0.4, 3)
                    sk_b = round((final_strike * 0.96) / 1000) * 1000
                    usdt = final_strike*a + sk_b*b
                    trade_txt = (f"1️⃣ `Sell P-{date_str}-{int(final_strike)} x {a}`\n"
                                 f"2️⃣ `Sell P-{date_str}-{int(sk_b)} x {b}`")
                else:
                    a = round(final_amt, 3)
                    usdt = final_strike * a
                    trade_txt = f"`Sell P-{date_str}-{int(final_strike)} x {a}`"
            
            icon = "✅" if final_amt > 0 else "🚫"
            warn = "\n⚠️ **注意**: 未扣除在途 Put！" if final_amt > 0 else ""
            
            return (
                f"🦈 **抄底策略 (Buy)**\n"
                f"══════════════════\n"
                f"💎 Price: `${p:,.0f}` | HV: `{hv*100:.1f}%`\n"
                f"🌊 Zone: **{zone}**\n"
                f"──────────────────\n"
                f"📊 **风控审计**\n"
                f"• 持仓: `{btc_holdings:.4f}`\n"
                f"• 额度: `{final_amt:.4f} BTC` {icon}\n"
                f"══════════════════\n"
                f"🚀 **{desc}** (Delta ~{delta})\n"
                f"{trade_txt}\n"
                f"💰 保证金: `${usdt:,.0f}`"
                f"{warn}"
            )
        except Exception as e:
            return f"Error: {e}"

    report = await asyncio.to_thread(run_strat)
    await msg.edit_text(report, parse_mode='Markdown')

# --- 🔥 新增: /sellcall (卖出端) ---
async def sellcall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    
    # 1. 解析成本价参数
    cost_basis = 0
    try:
        if context.args: cost_basis = float(context.args[0])
    except:
        await update.message.reply_text("❌ 参数错误。用法: `/sellcall [持仓成本]`\n例如: `/sellcall 65000`")
        return

    msg = await update.message.reply_text("⏳ 计算收租策略 (Sell Call)...")

    def run_strat():
        try:
            # 2. 获取数据
            res = _session.get(f"{BASE_URL_SPOT}/api/v3/klines", params={'symbol':'BTCUSDT','interval':'1d','limit':300}, timeout=10).json()
            closes = [float(k[4]) for k in res]
            stats = calculate_analytics(closes)
            p, ma, hv = closes[-1], stats['ma120'], stats['hv']
            sigma = min(2.0, max(0.40, hv * 1.1))

            # 3. 确定区域
            zone, delta, term, desc = get_call_zone(p/ma)

            # 4. 获取实际持仓 (作为 Call 的底层资产)
            real_data = get_real_total_balance()
            btc_holdings = real_data[0] if real_data else INITIAL_SPOT_HOLDINGS
            
            # 5. 核心判断
            if delta == 0:
                # 禁止卖Call区
                return (
                    f"🦅 **收租策略 (Sell)**\n"
                    f"══════════════════\n"
                    f"💎 Price: `${p:,.0f}` (r={p/ma:.2f})\n"
                    f"☁️ Zone: **{zone}**\n"
                    f"──────────────────\n"
                    f"🛑 **禁止操作**\n"
                    f"当前处于潜伏低估区，权利金过少且极易卖飞。\n"
                    f"💡 **建议**: 拿住现货，装死不动。"
                )
            
            # 6. 计算 Strike
            raw_strike = estimate_call_strike(p, delta, term, sigma)
            
            # 7. 风控：不亏本原则
            final_strike = raw_strike
            warning_txt = ""
            if cost_basis > 0:
                min_sell_price = cost_basis * 1.02 # 至少赚2%
                if raw_strike < min_sell_price:
                    final_strike = min_sell_price
                    warning_txt = f"\n⚠️ **风控触发**: 原Strike(${raw_strike:,.0f})低于保本价，已强制修正。"

            # 取整
            final_strike = round(final_strike / 500) * 500
            date_str = (datetime.now(timezone.utc) + timedelta(days=term)).strftime("%m-%d")
            
            # 8. 估算收益 (年化)
            # 粗略估算权利金 (仅供参考)
            est_premium_rate = delta * 0.2 * (term/30) # 经验估算
            est_income = final_strike * btc_holdings * est_premium_rate

            return (
                f"🦅 **收租策略 (Sell)**\n"
                f"══════════════════\n"
                f"💎 Price: `${p:,.0f}` (r={p/ma:.2f})\n"
                f"☁️ Zone: **{zone}**\n"
                f"📦 持仓: `{btc_holdings:.4f}` BTC\n"
                f"──────────────────\n"
                f"🚀 **{desc}** (Delta ~{delta})\n"
                f"🎯 **推荐开仓**:\n"
                f"`Sell C-{date_str}-{int(final_strike)}`\n"
                f"• 数量: 根据意愿 (建议 50% 持仓)\n"
                f"• 溢价率: `+{(final_strike/p-1)*100:.1f}%`\n"
                f"{warning_txt}"
            )

        except Exception as e:
            return f"Error: {e}"

    report = await asyncio.to_thread(run_strat)
    await msg.edit_text(report, parse_mode='Markdown')

# ================= 4. Main =================

async def income_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    msg = await update.message.reply_text("⏳ 正在计算睡后收入...")
    
    def run_calc():
        # 获取基础数据
        p_url = f"{BASE_URL_SPOT}/api/v3/ticker/price?symbol=BTCUSDT"
        price = float(_session.get(p_url, timeout=5).json()['price'])
        
        real_data = get_real_total_balance()
        if not real_data: return "❌ 无法获取持仓"
        
        btc_tot, usdt_tot, d = real_data
        earn_btc = d['earn_btc']
        earn_usdt = d['earn_usdt']
        
        # 获取 APR
        btc_apr = get_earn_apr('BTC')
        usdt_apr = get_earn_apr('USDT')
        if btc_apr == 0: btc_apr = 0.003 # 兜底 0.3%
        if usdt_apr == 0: usdt_apr = 0.05  # 兜底 5%

        # 计算收益
        daily_btc = earn_btc * btc_apr / 365
        daily_usdt = earn_usdt * usdt_apr / 365
        
        # 投影 (如果 BTC 涨到 10w)
        price_10w = 100000
        
        return (
            f"🛌 **睡后收入投影仪**\n"
            f"══════════════════\n"
            f"🏦 **理财本金**\n"
            f"• BTC: `{earn_btc:.4f}` (APR: {btc_apr*100:.2f}%)\n"
            f"• USDT: `{earn_usdt:,.0f}` (APR: {usdt_apr*100:.2f}%)\n"
            f"──────────────────\n"
            f"💸 **预计每日收益**\n"
            f"• BTC: `{daily_btc:.8f}`\n"
            f"• USDT: `{daily_usdt:.2f}`\n"
            f"• 总值: **`${(daily_btc*price + daily_usdt):.2f}` / 天**\n"
            f"──────────────────\n"
            f"🚀 **未来展望 (BTC=$10w)**\n"
            f"• 您的BTC利息将价值:\n"
            f"• `${(daily_btc * 30 * price_10w):.0f}` / 月\n"
            f"• `${(daily_btc * 365 * price_10w):.0f}` / 年\n"
            f"💡 *\"一顿猪脚饭已到账\"*"
        )
            
    report = await asyncio.to_thread(run_calc)
    await msg.edit_text(report, parse_mode='Markdown')

# ... sellput / sellcall unchanged ...

async def get_application():
    global _application
    if _application is None:
        _application = Application.builder().token(TG_BOT_TOKEN).build()
        _application.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("🤖 v5.1 Holder Edition Ready")))
        _application.add_handler(CommandHandler("market", market_command))
        _application.add_handler(CommandHandler("wallet", wallet_command))
        _application.add_handler(CommandHandler("income", income_command))
        _application.add_handler(CommandHandler("sellput", sellput_command))
        _application.add_handler(CommandHandler("sellcall", sellcall_command))
        
        # 🆕 注册 MyLedger 指令
        if LEDGER_ENABLED:
            register_ledger_handlers(_application)
            logger.info("✅ MyLedger 模块已加载")
        
        await _application.initialize()
    return _application

async def main_process(request):
    try:
        if MY_SECRET_TOKEN:
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_header != MY_SECRET_TOKEN:
                return "Unauthorized", 403

        app = await get_application()
        update = Update.de_json(request.get_json(force=True), app.bot)
        await app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Err: {e}")
        return "Error", 500

def telegram_bot(request):
    return asyncio.run(main_process(request))