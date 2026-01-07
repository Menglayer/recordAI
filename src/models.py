"""
MyLedger - 数据模型定义
使用 SQLAlchemy ORM 定义三张核心表
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Snapshot(Base):
    """资产快照表 - 记录每次盘点的持仓数量"""
    __tablename__ = 'snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    account_name = Column(String(100), nullable=False)  # 例如: Binance, OKX, IBKR
    symbol = Column(String(50), nullable=False)         # 例如: BTC, AAPL, USDT
    quantity = Column(Float, nullable=False)            # 持仓数量
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Snapshot(date={self.date}, account={self.account_name}, symbol={self.symbol}, qty={self.quantity})>"


class Transfer(Base):
    """资金流水表 - 记录外部资金进出（存入/提取）"""
    __tablename__ = 'transfers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # 'deposit' 或 'withdrawal'
    amount_usd = Column(Float, nullable=False)  # 金额（美元）
    note = Column(String(500), nullable=True)   # 备注
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Transfer(date={self.date}, type={self.type}, amount=${self.amount_usd})>"


class PriceHistory(Base):
    """价格历史表 - 存储各资产的历史价格"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    price_usd = Column(Float, nullable=False)
    source = Column(String(50), nullable=True)  # 价格来源: yfinance, ccxt, coingecko
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceHistory(date={self.date}, symbol={self.symbol}, price=${self.price_usd})>"


def get_engine(db_url='local_ledger.db'):
    """创建数据库引擎，支持 SQLite 和 PostgreSQL"""
    if "://" in db_url:
        # 确保使用 psycopg2 驱动
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
        # 自动添加 SSL 模式（Supabase 必须）
        if "sslmode" not in db_url:
            separator = "&" if "?" in db_url else "?"
            db_url += f"{separator}sslmode=require"
        
        # 增加连接池配置
        return create_engine(
            db_url, 
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"connect_timeout": 15}
        )
    return create_engine(f'sqlite:///{db_url}', echo=False)


def get_session(engine):
    """创建数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()
