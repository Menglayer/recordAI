"""
TG Bot 主入口
指令逻辑 + 路由注册
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 子模块
from binance_api import (
    get_real_total_balance, get_earn_apr, get_fng_index,
    fetch_klines, fetch_btc_price, fetch_funding_rate, fetch_24h_change,
)
from crypto_analytics import (
    calculate_analytics,
    get_risk_zone, estimate_strike,
    get_call_zone, estimate_call_strike,
)

# MyLedger 集成
try:
    from ledger_commands import register_ledger_handlers
    LEDGER_ENABLED = True
except ImportError:
    LEDGER_ENABLED = False

# ================= 配置 =================
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN', '').strip()
TG_CHAT_ID_ENV = os.environ.get('TG_CHAT_ID', '').strip()
MY_SECRET_TOKEN = os.environ.get('MY_SECRET_TOKEN', '').strip()

# 策略参数
TARGET_BTC_CAP = 3.0
DAILY_DCA_AMOUNT = 500.0
DCA_DAYS_PREDICTION = 30
INITIAL_SPOT_HOLDINGS = 0.04168

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

_application = None

# ================= 权限检查 =================

ALLOWED_IDS = set()
if TG_CHAT_ID_ENV:
    ALLOWED_IDS = set(int(x.strip()) for x in TG_CHAT_ID_ENV.split(',') if x.strip())


async def check_auth(update: Update):
    if update.effective_user.id in ALLOWED_IDS:
        return True
    await update.message.reply_text("⛔️ Denied")
    return False


# ================= /market 市场全景 =================

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    try:
        closes = fetch_klines(limit=800)
        p = closes[-1]
        stats = calculate_analytics(closes)

        fund = fetch_funding_rate()
        fng_val, fng_class = get_fng_index()
        chg = fetch_24h_change()

        rsi = stats.get('rsi', 50)
        rsi_state = "🔥超买" if rsi > 70 else ("❄️超卖" if rsi < 30 else "😐中性")
        bb_up, bb_low = stats.get('bb_up', 0), stats.get('bb_low', 0)

        # Ahr999 状态
        ahr = stats.get('ahr999', 99)
        if ahr < 0.45:
            ahr_state = "🟢 抄底 (Buy)"
        elif ahr < 1.2:
            ahr_state = "🟡 定投 (Hold)"
        elif ahr < 5.0:
            ahr_state = "🚀 起飞 (Sit)"
        else:
            ahr_state = "🏃 逃顶 (Top)"

        # 两年线
        ma730 = stats.get('ma730', 0)
        ma730_top = ma730 * 5
        ma730_status = f"距离逃顶: {((ma730_top / p) - 1) * 100:+.1f}%" if ma730 > 0 else "N/A"
        if p > ma730_top:
            ma730_status = "⚠️ **已破两年线顶!**"

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
            f"• 资金费率: `{fund * 100:.4f}%`\n"
            f"• 波动率HV: `{stats['hv'] * 100:.1f}%`\n"
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


# ================= /wallet 持仓审计 =================

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    msg = await update.message.reply_text("⏳ 由于是 Holder，正在用心审计...")

    def run_check():
        price = fetch_btc_price()
        real_data = get_real_total_balance()
        if real_data:
            btc_tot, usdt_tot, d = real_data
            tag = "🟢 **实盘 (RSA)**"
        else:
            btc_tot = INITIAL_SPOT_HOLDINGS
            usdt_tot = 0
            tag = "🟠 **模拟数据**"

        rem_btc = max(0.0, TARGET_BTC_CAP - btc_tot)
        rem_usdt = rem_btc * price
        days_to_finish = int(rem_usdt / DAILY_DCA_AMOUNT) if DAILY_DCA_AMOUNT > 0 else 9999
        finish_date = (datetime.now() + timedelta(days=days_to_finish)).strftime("%Y-%m")
        progress = (btc_tot / TARGET_BTC_CAP) * 100

        return (
            f"👛 **财富自由进度表**\n{tag}\n"
            f"══════════════════\n"
            f"📦 **核心资产**\n"
            f"• 总持仓: `{btc_tot:.4f} BTC`\n"
            f"• 市值: `${btc_tot * price:,.0f}`\n"
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


# ================= /sellput 抄底策略 =================

async def sellput_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    msg = await update.message.reply_text("⏳ 计算抄底策略...")

    def run_strat():
        try:
            closes = fetch_klines(limit=300)
            stats = calculate_analytics(closes)
            if not stats:
                return "⚠️ K线不足"
            p, ma, hv = closes[-1], stats['ma120'], stats['hv']
            sigma = min(2.0, max(0.40, hv * 1.1))

            real_data = get_real_total_balance()
            btc_holdings = real_data[0] if real_data else INITIAL_SPOT_HOLDINGS

            con_price = min(p, ma) * 0.9
            future_dca = (DAILY_DCA_AMOUNT * DCA_DAYS_PREDICTION) / con_price
            total_risk = btc_holdings + future_dca
            rem = TARGET_BTC_CAP - total_risk

            zone, pct, delta, term, desc = get_risk_zone(p / ma)
            final_amt = max(0.0, min(rem, (TARGET_BTC_CAP * pct) - btc_holdings))

            raw_strike = estimate_strike(p, delta, term, sigma)
            safe_raw = min(raw_strike, p * 0.96)
            final_strike = round(safe_raw / 1000) * 1000
            if final_strike >= p:
                final_strike -= 1000

            date_str = (datetime.now(timezone.utc) + timedelta(days=term)).strftime("%m-%d")
            trade_txt = ""
            usdt = 0

            if final_amt > 0:
                if final_amt >= 0.2:
                    a = round(final_amt * 0.6, 3)
                    b = round(final_amt * 0.4, 3)
                    sk_b = round((final_strike * 0.96) / 1000) * 1000
                    usdt = final_strike * a + sk_b * b
                    trade_txt = (
                        f"1️⃣ `Sell P-{date_str}-{int(final_strike)} x {a}`\n"
                        f"2️⃣ `Sell P-{date_str}-{int(sk_b)} x {b}`"
                    )
                else:
                    a = round(final_amt, 3)
                    usdt = final_strike * a
                    trade_txt = f"`Sell P-{date_str}-{int(final_strike)} x {a}`"

            icon = "✅" if final_amt > 0 else "🚫"
            warn = "\n⚠️ **注意**: 未扣除在途 Put！" if final_amt > 0 else ""

            return (
                f"🦈 **抄底策略 (Buy)**\n"
                f"══════════════════\n"
                f"💎 Price: `${p:,.0f}` | HV: `{hv * 100:.1f}%`\n"
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


# ================= /sellcall 收租策略 =================

async def sellcall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return

    cost_basis = 0
    try:
        if context.args:
            cost_basis = float(context.args[0])
    except Exception:
        await update.message.reply_text(
            "❌ 参数错误。用法: `/sellcall [持仓成本]`\n例如: `/sellcall 65000`"
        )
        return

    msg = await update.message.reply_text("⏳ 计算收租策略 (Sell Call)...")

    def run_strat():
        try:
            closes = fetch_klines(limit=300)
            stats = calculate_analytics(closes)
            p, ma, hv = closes[-1], stats['ma120'], stats['hv']
            sigma = min(2.0, max(0.40, hv * 1.1))

            zone, delta, term, desc = get_call_zone(p / ma)

            real_data = get_real_total_balance()
            btc_holdings = real_data[0] if real_data else INITIAL_SPOT_HOLDINGS

            if delta == 0:
                return (
                    f"🦅 **收租策略 (Sell)**\n"
                    f"══════════════════\n"
                    f"💎 Price: `${p:,.0f}` (r={p / ma:.2f})\n"
                    f"☁️ Zone: **{zone}**\n"
                    f"──────────────────\n"
                    f"🛑 **禁止操作**\n"
                    f"当前处于潜伏低估区，权利金过少且极易卖飞。\n"
                    f"💡 **建议**: 拿住现货，装死不动。"
                )

            raw_strike = estimate_call_strike(p, delta, term, sigma)

            final_strike = raw_strike
            warning_txt = ""
            if cost_basis > 0:
                min_sell_price = cost_basis * 1.02
                if raw_strike < min_sell_price:
                    final_strike = min_sell_price
                    warning_txt = (
                        f"\n⚠️ **风控触发**: 原Strike(${raw_strike:,.0f})"
                        f"低于保本价，已强制修正。"
                    )

            final_strike = round(final_strike / 500) * 500
            date_str = (datetime.now(timezone.utc) + timedelta(days=term)).strftime("%m-%d")


            return (
                f"🦅 **收租策略 (Sell)**\n"
                f"══════════════════\n"
                f"💎 Price: `${p:,.0f}` (r={p / ma:.2f})\n"
                f"☁️ Zone: **{zone}**\n"
                f"📦 持仓: `{btc_holdings:.4f}` BTC\n"
                f"──────────────────\n"
                f"🚀 **{desc}** (Delta ~{delta})\n"
                f"🎯 **推荐开仓**:\n"
                f"`Sell C-{date_str}-{int(final_strike)}`\n"
                f"• 数量: 根据意愿 (建议 50% 持仓)\n"
                f"• 溢价率: `+{(final_strike / p - 1) * 100:.1f}%`\n"
                f"{warning_txt}"
            )

        except Exception as e:
            return f"Error: {e}"

    report = await asyncio.to_thread(run_strat)
    await msg.edit_text(report, parse_mode='Markdown')


# ================= /income 睡后收入 =================

async def income_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    msg = await update.message.reply_text("⏳ 正在计算睡后收入...")

    def run_calc():
        price = fetch_btc_price()

        real_data = get_real_total_balance()
        if not real_data:
            return "❌ 无法获取持仓"

        btc_tot, usdt_tot, d = real_data
        earn_btc = d['earn_btc']
        earn_usdt = d['earn_usdt']

        btc_apr = get_earn_apr('BTC')
        usdt_apr = get_earn_apr('USDT')
        if btc_apr == 0:
            btc_apr = 0.003
        if usdt_apr == 0:
            usdt_apr = 0.05

        daily_btc = earn_btc * btc_apr / 365
        daily_usdt = earn_usdt * usdt_apr / 365

        price_10w = 100000

        return (
            f"🛌 **睡后收入投影仪**\n"
            f"══════════════════\n"
            f"🏦 **理财本金**\n"
            f"• BTC: `{earn_btc:.4f}` (APR: {btc_apr * 100:.2f}%)\n"
            f"• USDT: `{earn_usdt:,.0f}` (APR: {usdt_apr * 100:.2f}%)\n"
            f"──────────────────\n"
            f"💸 **预计每日收益**\n"
            f"• BTC: `{daily_btc:.8f}`\n"
            f"• USDT: `{daily_usdt:.2f}`\n"
            f"• 总值: **`${(daily_btc * price + daily_usdt):.2f}` / 天**\n"
            f"──────────────────\n"
            f"🚀 **未来展望 (BTC=$10w)**\n"
            f"• 您的BTC利息将价值:\n"
            f"• `${(daily_btc * 30 * price_10w):.0f}` / 月\n"
            f"• `${(daily_btc * 365 * price_10w):.0f}` / 年\n"
            f'💡 *"一顿猪脚饭已到账"*'
        )

    report = await asyncio.to_thread(run_calc)
    await msg.edit_text(report, parse_mode='Markdown')


# ================= 应用初始化 =================

async def get_application():
    global _application
    if _application is None:
        _application = Application.builder().token(TG_BOT_TOKEN).build()
        _application.add_handler(CommandHandler(
            "start", lambda u, c: u.message.reply_text("🤖 v5.2 Holder Edition Ready")
        ))
        _application.add_handler(CommandHandler("market", market_command))
        _application.add_handler(CommandHandler("wallet", wallet_command))
        _application.add_handler(CommandHandler("income", income_command))
        _application.add_handler(CommandHandler("sellput", sellput_command))
        _application.add_handler(CommandHandler("sellcall", sellcall_command))

        # MyLedger 集成
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