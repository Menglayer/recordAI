"""
MyLedger TG Bot 集成模块
实现通过 Telegram 查看和录入资产数据
"""
import os
import logging
from datetime import datetime, date
from telegram import Update
from telegram.ext import ContextTypes

# 数据库依赖
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# ================= 数据库配置 =================
# 从环境变量获取数据库 URL (与 Streamlit 共享)
LEDGER_DB_URL = os.environ.get('LEDGER_DB_URL', '').strip()

Base = declarative_base()

# ================= 数据模型 (与 src/models.py 保持一致) =================
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
    type = Column(String(20), nullable=False)  # 'deposit' or 'withdrawal'
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


# ================= 数据库连接 =================
_engine = None
_Session = None

def get_db_session():
    """获取数据库会话"""
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


# ================= 数据查询函数 =================

def get_latest_snapshot_date():
    """获取最新快照日期"""
    session = get_db_session()
    if not session:
        return None
    try:
        result = session.query(Snapshot.date).order_by(desc(Snapshot.date)).first()
        return result[0] if result else None
    finally:
        session.close()

def get_price(symbol, target_date=None):
    """获取资产价格"""
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
    """计算最新净值"""
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
        
        # 按账户汇总
        by_account = {}
        for h in holdings:
            acc = h['account']
            if acc not in by_account:
                by_account[acc] = 0
            by_account[acc] += h['value']
        
        # 按资产汇总
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
    """计算盈亏"""
    session = get_db_session()
    if not session:
        return None
    
    try:
        # 计算净投入
        deposits = session.query(func.sum(Transfer.amount_usd)).filter(Transfer.type == 'deposit').scalar() or 0
        withdrawals = session.query(func.sum(Transfer.amount_usd)).filter(Transfer.type == 'withdrawal').scalar() or 0
        net_investment = deposits - withdrawals
        
        # 获取当前净值
        nw_data = calculate_net_worth()
        current_nw = nw_data['total'] if nw_data else 0
        
        # 计算 PnL
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


# ================= Telegram 指令 =================

async def ledger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ledger - 查看资产概览
    """
    msg = await update.message.reply_text("⏳ 正在获取 MyLedger 数据...")
    
    try:
        nw_data = calculate_net_worth()
        pnl_data = calculate_pnl()
        
        if not nw_data:
            await msg.edit_text("❌ 暂无数据，请先在 Web 端录入快照")
            return
        
        # 格式化输出
        total = nw_data['total']
        pnl = pnl_data['pnl'] if pnl_data else 0
        roi = pnl_data['roi'] if pnl_data else 0
        
        pnl_icon = "📈" if pnl >= 0 else "📉"
        pnl_color = "+" if pnl >= 0 else ""
        
        # 账户明细
        account_lines = []
        for acc, val in sorted(nw_data['by_account'].items(), key=lambda x: -x[1]):
            pct = (val / total * 100) if total > 0 else 0
            account_lines.append(f"• {acc}: `${val:,.0f}` ({pct:.1f}%)")
        
        accounts_text = "\n".join(account_lines[:5])  # 最多显示5个
        if len(account_lines) > 5:
            accounts_text += f"\n• ... 还有 {len(account_lines)-5} 个账户"
        
        report = (
            f"💰 **MyLedger 资产概览**\n"
            f"══════════════════\n"
            f"📅 数据日期: `{nw_data['date']}`\n"
            f"──────────────────\n"
            f"💵 **总净值**: `${total:,.0f}`\n"
            f"{pnl_icon} **盈亏**: `{pnl_color}${pnl:,.0f}` ({pnl_color}{roi:.1f}%)\n"
            f"──────────────────\n"
            f"🏦 **账户分布**\n"
            f"{accounts_text}\n"
            f"──────────────────\n"
            f"💡 使用 /holdings 查看详细持仓"
        )
        
        await msg.edit_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ledger Error: {e}")
        await msg.edit_text(f"❌ 获取数据失败: {e}")


async def holdings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /holdings - 查看持仓明细
    """
    msg = await update.message.reply_text("⏳ 正在获取持仓明细...")
    
    try:
        nw_data = calculate_net_worth()
        
        if not nw_data:
            await msg.edit_text("❌ 暂无数据")
            return
        
        # 按资产汇总
        lines = []
        for sym, data in sorted(nw_data['by_symbol'].items(), key=lambda x: -x[1]['value']):
            qty = data['quantity']
            val = data['value']
            pct = (val / nw_data['total'] * 100) if nw_data['total'] > 0 else 0
            
            # 根据资产类型选择图标
            icon = "🪙" if sym in ['BTC', 'ETH'] else "💵" if sym == 'USDT' else "📊"
            lines.append(f"{icon} **{sym}**: `{qty:,.4f}` → `${val:,.0f}` ({pct:.1f}%)")
        
        holdings_text = "\n".join(lines[:10])
        if len(lines) > 10:
            holdings_text += f"\n... 还有 {len(lines)-10} 个资产"
        
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


async def snapshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /snapshot <账户> <资产1> <数量1> [资产2] [数量2] ...
    例如: /snapshot Binance BTC 0.5 USDT 10000
    """
    args = context.args
    
    if len(args) < 3 or len(args) % 2 == 0:
        await update.message.reply_text(
            "📸 **快照录入**\n\n"
            "用法: `/snapshot <账户> <资产> <数量> [资产2] [数量2] ...`\n\n"
            "示例:\n"
            "• `/snapshot Binance BTC 0.5`\n"
            "• `/snapshot OKX BTC 1.2 USDT 5000 ETH 10`",
            parse_mode='Markdown'
        )
        return
    
    account = args[0]
    pairs = []
    for i in range(1, len(args), 2):
        symbol = args[i].upper()
        try:
            quantity = float(args[i+1])
            pairs.append((symbol, quantity))
        except ValueError:
            await update.message.reply_text(f"❌ 数量格式错误: {args[i+1]}")
            return
    
    session = get_db_session()
    if not session:
        await update.message.reply_text("❌ 数据库连接失败，请检查 LEDGER_DB_URL")
        return
    
    try:
        today = date.today()
        
        # 删除今天该账户的旧记录
        session.query(Snapshot).filter(
            Snapshot.date == today,
            Snapshot.account_name == account
        ).delete()
        
        # 插入新记录
        for symbol, quantity in pairs:
            snapshot = Snapshot(
                date=today,
                account_name=account,
                symbol=symbol,
                quantity=quantity
            )
            session.add(snapshot)
        
        session.commit()
        
        # 格式化确认信息
        items = "\n".join([f"• {sym}: `{qty:,.4f}`" for sym, qty in pairs])
        await update.message.reply_text(
            f"✅ **快照已保存**\n\n"
            f"📅 日期: `{today}`\n"
            f"🏦 账户: `{account}`\n"
            f"──────────────────\n"
            f"{items}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Snapshot Error: {e}")
        await update.message.reply_text(f"❌ 保存失败: {e}")
    finally:
        session.close()


async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /transfer <类型> <金额> [备注]
    类型: deposit (入金) / withdrawal (出金)
    例如: /transfer deposit 5000 工资
    """
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "💸 **转账录入**\n\n"
            "用法: `/transfer <类型> <金额> [备注]`\n\n"
            "类型:\n"
            "• `deposit` - 入金\n"
            "• `withdrawal` - 出金\n\n"
            "示例:\n"
            "• `/transfer deposit 5000 工资`\n"
            "• `/transfer withdrawal 1000 提现`",
            parse_mode='Markdown'
        )
        return
    
    transfer_type = args[0].lower()
    if transfer_type not in ['deposit', 'withdrawal']:
        await update.message.reply_text("❌ 类型必须是 deposit 或 withdrawal")
        return
    
    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("❌ 金额格式错误")
        return
    
    note = " ".join(args[2:]) if len(args) > 2 else None
    
    session = get_db_session()
    if not session:
        await update.message.reply_text("❌ 数据库连接失败")
        return
    
    try:
        transfer = Transfer(
            date=date.today(),
            type=transfer_type,
            amount_usd=amount,
            note=note
        )
        session.add(transfer)
        session.commit()
        
        type_icon = "📥" if transfer_type == 'deposit' else "📤"
        type_text = "入金" if transfer_type == 'deposit' else "出金"
        note_text = f"\n📝 备注: {note}" if note else ""
        
        await update.message.reply_text(
            f"✅ **转账已记录**\n\n"
            f"{type_icon} 类型: {type_text}\n"
            f"💵 金额: `${amount:,.0f}`"
            f"{note_text}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Transfer Error: {e}")
        await update.message.reply_text(f"❌ 保存失败: {e}")
    finally:
        session.close()


# ================= 注册指令 =================

def register_ledger_handlers(application):
    """注册 MyLedger 相关指令到 TG Bot"""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("ledger", ledger_command))
    application.add_handler(CommandHandler("holdings", holdings_command))
    application.add_handler(CommandHandler("snapshot", snapshot_command))
    application.add_handler(CommandHandler("transfer", transfer_command))
    
    logger.info("✅ MyLedger commands registered")
