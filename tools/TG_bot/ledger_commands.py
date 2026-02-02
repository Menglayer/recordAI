"""
MyLedger TG Bot 集成模块
实现通过 Telegram 查看和录入资产数据
支持交互式点选录入
"""
import os
import logging
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

# 数据库依赖
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# ================= 配置 =================
TG_CHAT_ID_ENV = os.environ.get('TG_CHAT_ID', '').strip()
ALLOWED_IDS = set()
if TG_CHAT_ID_ENV:
    ALLOWED_IDS = set(int(x.strip()) for x in TG_CHAT_ID_ENV.split(',') if x.strip())

LEDGER_DB_URL = os.environ.get('LEDGER_DB_URL', '').strip()

# 支持的币种
SUPPORTED_SYMBOLS = ['USDT', 'BTC', 'ETH']

# 用户会话状态 (内存存储，适合单用户)
user_sessions = {}

async def check_auth(update: Update):
    """检查用户权限"""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id in ALLOWED_IDS:
        return True
    if update.message:
        await update.message.reply_text("⛔️ 无权限访问 MyLedger")
    elif update.callback_query:
        await update.callback_query.answer("⛔️ 无权限", show_alert=True)
    return False

async def check_auth_callback(update: Update):
    """检查 callback 权限"""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id in ALLOWED_IDS:
        return True
    await update.callback_query.answer("⛔️ 无权限", show_alert=True)
    return False


# ================= 数据库 =================
Base = declarative_base()
from sqlalchemy import Column, Integer, String, Float, Date, DateTime

class Snapshot(Base):
    __tablename__ = 'snapshots'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    account_name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transfer(Base):
    __tablename__ = 'transfers'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    type = Column(String(20), nullable=False)
    amount_usd = Column(Float, nullable=False)
    note = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    symbol = Column(String(20), nullable=False)
    price_usd = Column(Float, nullable=False)
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

_engine = None
_Session = None

def get_db_session():
    global _engine, _Session
    if not LEDGER_DB_URL:
        return None
    if _engine is None:
        try:
            _engine = create_engine(LEDGER_DB_URL)
            _Session = sessionmaker(bind=_engine)
        except Exception as e:
            logger.error(f"DB Connection Error: {e}")
            return None
    return _Session()

def get_existing_accounts():
    """获取已有账户列表"""
    session = get_db_session()
    if not session:
        return []
    try:
        result = session.query(Snapshot.account_name).distinct().all()
        return [r[0] for r in result]
    finally:
        session.close()


# ================= 数据查询 =================

def get_latest_snapshot_date():
    session = get_db_session()
    if not session:
        return None
    try:
        result = session.query(Snapshot.date).order_by(desc(Snapshot.date)).first()
        return result[0] if result else None
    finally:
        session.close()

def get_price(symbol, target_date=None):
    session = get_db_session()
    if not session:
        return 0
    try:
        query = session.query(PriceHistory).filter(PriceHistory.symbol == symbol)
        if target_date:
            query = query.filter(PriceHistory.date <= target_date)
        price = query.order_by(desc(PriceHistory.date)).first()
        return price.price_usd if price else 0
    finally:
        session.close()

def calculate_net_worth():
    session = get_db_session()
    if not session:
        return None
    try:
        latest_date = get_latest_snapshot_date()
        if not latest_date:
            return None
        snapshots = session.query(Snapshot).filter(Snapshot.date == latest_date).all()
        
        total_value = 0
        holdings = []
        for s in snapshots:
            price = get_price(s.symbol, latest_date)
            value = s.quantity * price
            total_value += value
            holdings.append({
                'account': s.account_name,
                'symbol': s.symbol,
                'quantity': s.quantity,
                'price': price,
                'value': value
            })
        
        by_account = {}
        for h in holdings:
            acc = h['account']
            if acc not in by_account:
                by_account[acc] = 0
            by_account[acc] += h['value']
        
        by_symbol = {}
        for h in holdings:
            sym = h['symbol']
            if sym not in by_symbol:
                by_symbol[sym] = {'quantity': 0, 'value': 0}
            by_symbol[sym]['quantity'] += h['quantity']
            by_symbol[sym]['value'] += h['value']
        
        return {
            'date': latest_date,
            'total': total_value,
            'by_account': by_account,
            'by_symbol': by_symbol,
            'holdings': holdings
        }
    finally:
        session.close()

def calculate_pnl():
    session = get_db_session()
    if not session:
        return None
    try:
        deposits = session.query(func.sum(Transfer.amount_usd)).filter(Transfer.type == 'deposit').scalar() or 0
        withdrawals = session.query(func.sum(Transfer.amount_usd)).filter(Transfer.type == 'withdrawal').scalar() or 0
        net_investment = deposits - withdrawals
        nw_data = calculate_net_worth()
        current_nw = nw_data['total'] if nw_data else 0
        pnl = current_nw - net_investment
        roi = (pnl / net_investment * 100) if net_investment > 0 else 0
        return {
            'deposits': deposits,
            'withdrawals': withdrawals,
            'net_investment': net_investment,
            'current_nw': current_nw,
            'pnl': pnl,
            'roi': roi
        }
    finally:
        session.close()


# ================= /backup 数据备份 =================

import json
import io

def export_all_data():
    """导出所有数据"""
    session = get_db_session()
    if not session:
        return None
    
    try:
        # 导出快照
        snapshots = session.query(Snapshot).all()
        snapshots_data = [{
            'id': s.id,
            'date': str(s.date),
            'account_name': s.account_name,
            'symbol': s.symbol,
            'quantity': s.quantity,
            'created_at': str(s.created_at) if s.created_at else None
        } for s in snapshots]
        
        # 导出转账
        transfers = session.query(Transfer).all()
        transfers_data = [{
            'id': t.id,
            'date': str(t.date),
            'type': t.type,
            'amount_usd': t.amount_usd,
            'note': t.note,
            'created_at': str(t.created_at) if t.created_at else None
        } for t in transfers]
        
        # 导出价格
        prices = session.query(PriceHistory).all()
        prices_data = [{
            'id': p.id,
            'date': str(p.date),
            'symbol': p.symbol,
            'price_usd': p.price_usd,
            'source': p.source,
            'created_at': str(p.created_at) if p.created_at else None
        } for p in prices]
        
        return {
            'export_time': str(datetime.utcnow()),
            'snapshots': snapshots_data,
            'transfers': transfers_data,
            'prices': prices_data,
            'summary': {
                'total_snapshots': len(snapshots_data),
                'total_transfers': len(transfers_data),
                'total_prices': len(prices_data)
            }
        }
    finally:
        session.close()


def generate_restore_sql(data):
    """生成恢复用的 SQL 语句"""
    sql_lines = []
    sql_lines.append("-- MyLedger Backup")
    sql_lines.append(f"-- Exported at: {data['export_time']}")
    sql_lines.append("")
    
    # 快照
    sql_lines.append("-- Snapshots")
    for s in data['snapshots']:
        sql_lines.append(
            f"INSERT INTO snapshots (date, account_name, symbol, quantity) "
            f"VALUES ('{s['date']}', '{s['account_name']}', '{s['symbol']}', {s['quantity']});"
        )
    
    sql_lines.append("")
    sql_lines.append("-- Transfers")
    for t in data['transfers']:
        note = t['note'].replace("'", "''") if t['note'] else ''
        sql_lines.append(
            f"INSERT INTO transfers (date, type, amount_usd, note) "
            f"VALUES ('{t['date']}', '{t['type']}', {t['amount_usd']}, '{note}');"
        )
    
    sql_lines.append("")
    sql_lines.append("-- Prices")
    for p in data['prices']:
        source = p['source'].replace("'", "''") if p['source'] else ''
        sql_lines.append(
            f"INSERT INTO price_history (date, symbol, price_usd, source) "
            f"VALUES ('{p['date']}', '{p['symbol']}', {p['price_usd']}, '{source}');"
        )
    
    return "\n".join(sql_lines)


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /backup - 备份所有数据
    """
    if not await check_auth(update):
        return
    
    msg = await update.message.reply_text("⏳ 正在导出数据...")
    
    try:
        data = export_all_data()
        
        if not data:
            await msg.edit_text("❌ 数据库连接失败")
            return
        
        summary = data['summary']
        
        # 生成 JSON 文件
        json_content = json.dumps(data, ensure_ascii=False, indent=2)
        json_file = io.BytesIO(json_content.encode('utf-8'))
        json_file.name = f"myledger_backup_{date.today()}.json"
        
        # 生成 SQL 文件
        sql_content = generate_restore_sql(data)
        sql_file = io.BytesIO(sql_content.encode('utf-8'))
        sql_file.name = f"myledger_restore_{date.today()}.sql"
        
        await msg.edit_text(
            f"✅ *数据导出完成*\n\n"
            f"📊 *统计*\n"
            f"• 快照记录: `{summary['total_snapshots']}` 条\n"
            f"• 转账记录: `{summary['total_transfers']}` 条\n"
            f"• 价格记录: `{summary['total_prices']}` 条\n\n"
            f"📁 正在发送备份文件...",
            parse_mode='Markdown'
        )
        
        # 发送 JSON 文件
        json_file.seek(0)
        await update.message.reply_document(
            document=json_file,
            filename=json_file.name,
            caption="📦 JSON 备份 (完整数据)"
        )
        
        # 发送 SQL 文件
        sql_file.seek(0)
        await update.message.reply_document(
            document=sql_file,
            filename=sql_file.name,
            caption="🔧 SQL 恢复脚本 (可直接执行)"
        )
        
        await update.message.reply_text(
            "✅ *备份完成！*\n\n"
            "💡 *恢复方法*:\n"
            "1. JSON: 使用 /restore 命令\n"
            "2. SQL: 在数据库中直接执行\n\n"
            "⚠️ 建议定期备份，保存到安全位置",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Backup Error: {e}")
        await msg.edit_text(f"❌ 备份失败: {e}")


# ================= /ledger 查看概览 =================

def make_progress_bar(percentage, length=10):
    """生成进度条"""
    filled = int(percentage / 100 * length)
    empty = length - filled
    return '▓' * filled + '░' * empty

async def ledger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    msg = await update.message.reply_text("⏳ 正在获取数据...")
    
    try:
        nw_data = calculate_net_worth()
        pnl_data = calculate_pnl()
        
        if not nw_data:
            await msg.edit_text("❌ 暂无数据，请先录入快照\n\n使用 /snapshot 开始录入")
            return
        
        total = nw_data['total']
        pnl = pnl_data['pnl'] if pnl_data else 0
        roi = pnl_data['roi'] if pnl_data else 0
        
        # 盈亏状态
        if pnl > 0:
            pnl_icon = "🟢"
            pnl_status = "盈利"
        elif pnl < 0:
            pnl_icon = "🔴"
            pnl_status = "亏损"
        else:
            pnl_icon = "⚪"
            pnl_status = "持平"
        
        pnl_sign = "+" if pnl >= 0 else ""
        
        # 账户分布（美化版）
        account_lines = []
        sorted_accounts = sorted(nw_data['by_account'].items(), key=lambda x: -x[1])
        
        for i, (acc, val) in enumerate(sorted_accounts[:5]):
            pct = (val / total * 100) if total > 0 else 0
            bar = make_progress_bar(pct, 8)
            
            # 添加排名图标
            if i == 0:
                rank = "🥇"
            elif i == 1:
                rank = "🥈"
            elif i == 2:
                rank = "🥉"
            else:
                rank = "  "
            
            account_lines.append(f"{rank} `{acc}`\n     {bar} `${val:,.0f}` ({pct:.1f}%)")
        
        # 如果还有更多账户
        remaining = len(sorted_accounts) - 5
        if remaining > 0:
            account_lines.append(f"\n     📦 还有 {remaining} 个账户...")
        
        accounts_text = "\n".join(account_lines)
        
        # 获取 BTC 价格计算币本位
        btc_price = get_price('BTC') or 100000  # 默认价格
        btc_equivalent = total / btc_price if btc_price > 0 else 0
        
        report = (
            f"💰 *MyLedger 资产概览*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"📅 *数据日期*: `{nw_data['date']}`\n"
            f"\n"
            f"💵 *总净值*\n"
            f"   `$ {total:,.0f}`\n"
            f"   ≈ `{btc_equivalent:.4f} BTC`\n"
            f"\n"
            f"{pnl_icon} *{pnl_status}*: `{pnl_sign}${abs(pnl):,.0f}` ({pnl_sign}{roi:.1f}%)\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 *账户分布*\n"
            f"\n"
            f"{accounts_text}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 /holdings · 📸 /snapshot"
        )
        
        await msg.edit_text(report, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ledger Error: {e}")
        await msg.edit_text(f"❌ 获取失败: {e}")


# ================= /holdings 持仓明细 =================

async def holdings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    msg = await update.message.reply_text("⏳ 正在获取持仓明细...")
    
    try:
        nw_data = calculate_net_worth()
        if not nw_data:
            await msg.edit_text("❌ 暂无数据")
            return
        
        lines = []
        for sym, data in sorted(nw_data['by_symbol'].items(), key=lambda x: -x[1]['value']):
            qty = data['quantity']
            val = data['value']
            pct = (val / nw_data['total'] * 100) if nw_data['total'] > 0 else 0
            icon = "🪙" if sym in ['BTC', 'ETH'] else "💵" if sym == 'USDT' else "📊"
            lines.append(f"{icon} **{sym}**: `{qty:,.4f}` → `${val:,.0f}` ({pct:.1f}%)")
        
        holdings_text = "\n".join(lines[:10])
        
        report = (
            f"📋 **持仓明细**\n"
            f"══════════════════\n"
            f"📅 `{nw_data['date']}`\n"
            f"──────────────────\n"
            f"{holdings_text}\n"
            f"──────────────────\n"
            f"💰 总计: `${nw_data['total']:,.0f}`"
        )
        
        await msg.edit_text(report, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Holdings Error: {e}")
        await msg.edit_text(f"❌ 获取失败: {e}")


# ================= /snapshot 交互式录入 =================

async def snapshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始交互式快照录入"""
    if not await check_auth(update):
        return
    
    user_id = update.effective_user.id
    
    # 获取已有账户
    accounts = get_existing_accounts()
    
    # 构建键盘
    keyboard = []
    
    # 已有账户按钮
    for acc in accounts[:6]:  # 最多显示6个
        keyboard.append([InlineKeyboardButton(f"🏦 {acc}", callback_data=f"snap_acc:{acc}")])
    
    # 新建账户按钮
    keyboard.append([InlineKeyboardButton("➕ 新建账户", callback_data="snap_new_acc")])
    keyboard.append([InlineKeyboardButton("❌ 取消", callback_data="snap_cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📸 **快照录入 (Step 1/3)**\n\n"
        "请选择账户：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def snapshot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理快照录入的回调"""
    query = update.callback_query
    await query.answer()
    
    if not await check_auth_callback(update):
        return
    
    user_id = update.effective_user.id
    data = query.data
    
    # 取消操作
    if data == "snap_cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_text("❌ 已取消录入")
        return
    
    # 选择已有账户
    if data.startswith("snap_acc:"):
        account = data.split(":", 1)[1]
        user_sessions[user_id] = {'account': account, 'step': 'symbol'}
        
        # 显示币种选择
        keyboard = [
            [
                InlineKeyboardButton("💵 USDT", callback_data="snap_sym:USDT"),
                InlineKeyboardButton("🪙 BTC", callback_data="snap_sym:BTC"),
                InlineKeyboardButton("🔷 ETH", callback_data="snap_sym:ETH"),
            ],
            [InlineKeyboardButton("❌ 取消", callback_data="snap_cancel")]
        ]
        
        await query.edit_message_text(
            f"📸 **快照录入 (Step 2/3)**\n\n"
            f"🏦 账户: `{account}`\n\n"
            f"请选择币种：",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    # 新建账户
    if data == "snap_new_acc":
        user_sessions[user_id] = {'step': 'new_account'}
        await query.edit_message_text(
            "📸 **快照录入 - 新建账户**\n\n"
            "请直接输入账户名称：\n"
            "（例如：Binance, OKX, Bitget）",
            parse_mode='Markdown'
        )
        return
    
    # 选择币种
    if data.startswith("snap_sym:"):
        symbol = data.split(":", 1)[1]
        session = user_sessions.get(user_id, {})
        session['symbol'] = symbol
        session['step'] = 'quantity'
        user_sessions[user_id] = session
        
        await query.edit_message_text(
            f"📸 **快照录入 (Step 3/3)**\n\n"
            f"🏦 账户: `{session['account']}`\n"
            f"💰 币种: `{symbol}`\n\n"
            f"请输入数量：\n"
            f"（直接发送数字，如：0.5 或 10000）",
            parse_mode='Markdown'
        )
        return


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户文本输入（用于快照录入流程）"""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    
    if not session:
        return  # 不在录入流程中，忽略
    
    text = update.message.text.strip()
    step = session.get('step')
    
    # 新建账户 - 输入账户名
    if step == 'new_account':
        account = text
        user_sessions[user_id] = {'account': account, 'step': 'symbol'}
        
        keyboard = [
            [
                InlineKeyboardButton("💵 USDT", callback_data="snap_sym:USDT"),
                InlineKeyboardButton("🪙 BTC", callback_data="snap_sym:BTC"),
                InlineKeyboardButton("🔷 ETH", callback_data="snap_sym:ETH"),
            ],
            [InlineKeyboardButton("❌ 取消", callback_data="snap_cancel")]
        ]
        
        await update.message.reply_text(
            f"📸 **快照录入 (Step 2/3)**\n\n"
            f"🏦 账户: `{account}` ✅\n\n"
            f"请选择币种：",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    # 输入数量
    if step == 'quantity':
        try:
            quantity = float(text.replace(',', ''))
        except ValueError:
            await update.message.reply_text("❌ 数量格式错误，请输入数字")
            return
        
        account = session['account']
        symbol = session['symbol']
        
        # 保存到数据库
        db_session = get_db_session()
        if not db_session:
            await update.message.reply_text("❌ 数据库连接失败")
            user_sessions.pop(user_id, None)
            return
        
        try:
            today = date.today()
            
            # 删除今天该账户该币种的旧记录
            db_session.query(Snapshot).filter(
                Snapshot.date == today,
                Snapshot.account_name == account,
                Snapshot.symbol == symbol
            ).delete()
            
            # 插入新记录
            snapshot = Snapshot(
                date=today,
                account_name=account,
                symbol=symbol,
                quantity=quantity
            )
            db_session.add(snapshot)
            db_session.commit()
            
            # 清理会话
            user_sessions.pop(user_id, None)
            
            # 构建继续录入按钮
            keyboard = [
                [InlineKeyboardButton("➕ 继续录入同账户", callback_data=f"snap_acc:{account}")],
                [InlineKeyboardButton("🏦 换个账户", callback_data="snap_restart")],
                [InlineKeyboardButton("✅ 完成", callback_data="snap_done")]
            ]
            
            await update.message.reply_text(
                f"✅ **快照已保存！**\n\n"
                f"📅 日期: `{today}`\n"
                f"🏦 账户: `{account}`\n"
                f"💰 币种: `{symbol}`\n"
                f"📊 数量: `{quantity:,.4f}`\n\n"
                f"还要继续录入吗？",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Snapshot Save Error: {e}")
            await update.message.reply_text(f"❌ 保存失败: {e}")
            user_sessions.pop(user_id, None)
        finally:
            db_session.close()


async def snapshot_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """完成录入"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "snap_done":
        await query.edit_message_text("✅ 录入完成！使用 /ledger 查看资产概览")
    elif query.data == "snap_restart":
        # 重新开始
        accounts = get_existing_accounts()
        keyboard = []
        for acc in accounts[:6]:
            keyboard.append([InlineKeyboardButton(f"🏦 {acc}", callback_data=f"snap_acc:{acc}")])
        keyboard.append([InlineKeyboardButton("➕ 新建账户", callback_data="snap_new_acc")])
        keyboard.append([InlineKeyboardButton("❌ 取消", callback_data="snap_cancel")])
        
        await query.edit_message_text(
            "📸 **快照录入 (Step 1/3)**\n\n"
            "请选择账户：",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )


# ================= /transfer 转账录入 =================

async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """交互式转账录入"""
    if not await check_auth(update):
        return
    
    user_id = update.effective_user.id
    
    keyboard = [
        [
            InlineKeyboardButton("📥 入金 (Deposit)", callback_data="trans_type:deposit"),
            InlineKeyboardButton("📤 出金 (Withdrawal)", callback_data="trans_type:withdrawal"),
        ],
        [InlineKeyboardButton("❌ 取消", callback_data="trans_cancel")]
    ]
    
    await update.message.reply_text(
        "💸 **转账录入**\n\n"
        "请选择类型：",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理转账回调"""
    query = update.callback_query
    await query.answer()
    
    if not await check_auth_callback(update):
        return
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "trans_cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_text("❌ 已取消")
        return
    
    if data.startswith("trans_type:"):
        trans_type = data.split(":", 1)[1]
        user_sessions[user_id] = {'trans_type': trans_type, 'step': 'amount'}
        
        type_text = "入金" if trans_type == 'deposit' else "出金"
        await query.edit_message_text(
            f"💸 **转账录入 - {type_text}**\n\n"
            f"请输入金额 (USD)：\n"
            f"（直接发送数字，如：5000）",
            parse_mode='Markdown'
        )


async def handle_transfer_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理转账金额输入"""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    
    if not session or 'trans_type' not in session:
        return
    
    if session.get('step') != 'amount':
        return
    
    text = update.message.text.strip()
    
    try:
        amount = float(text.replace(',', ''))
    except ValueError:
        await update.message.reply_text("❌ 金额格式错误，请输入数字")
        return
    
    trans_type = session['trans_type']
    
    db_session = get_db_session()
    if not db_session:
        await update.message.reply_text("❌ 数据库连接失败")
        user_sessions.pop(user_id, None)
        return
    
    try:
        transfer = Transfer(
            date=date.today(),
            type=trans_type,
            amount_usd=amount,
            note=None
        )
        db_session.add(transfer)
        db_session.commit()
        
        user_sessions.pop(user_id, None)
        
        type_icon = "📥" if trans_type == 'deposit' else "📤"
        type_text = "入金" if trans_type == 'deposit' else "出金"
        
        await update.message.reply_text(
            f"✅ **转账已记录！**\n\n"
            f"{type_icon} 类型: {type_text}\n"
            f"💵 金额: `${amount:,.0f}`\n"
            f"📅 日期: `{date.today()}`",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Transfer Error: {e}")
        await update.message.reply_text(f"❌ 保存失败: {e}")
        user_sessions.pop(user_id, None)
    finally:
        db_session.close()


# ================= 通用文本处理 =================

async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """统一处理文本输入"""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    
    if not session:
        return  # 不在任何流程中
    
    # 快照流程
    if 'account' in session or session.get('step') == 'new_account':
        await handle_text_input(update, context)
        return
    
    # 转账流程
    if 'trans_type' in session:
        await handle_transfer_input(update, context)
        return


# ================= 注册指令 =================

def register_ledger_handlers(application):
    """注册 MyLedger 相关指令到 TG Bot"""
    from telegram.ext import CommandHandler
    
    # 命令
    application.add_handler(CommandHandler("ledger", ledger_command))
    application.add_handler(CommandHandler("holdings", holdings_command))
    application.add_handler(CommandHandler("snapshot", snapshot_command))
    application.add_handler(CommandHandler("transfer", transfer_command))
    application.add_handler(CommandHandler("backup", backup_command))
    
    # 回调处理
    application.add_handler(CallbackQueryHandler(snapshot_callback, pattern=r'^snap_'))
    application.add_handler(CallbackQueryHandler(snapshot_done_callback, pattern=r'^snap_(done|restart)$'))
    application.add_handler(CallbackQueryHandler(transfer_callback, pattern=r'^trans_'))
    
    # 文本输入处理 (放在最后，优先级最低)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))
    
    logger.info("✅ MyLedger commands registered")
