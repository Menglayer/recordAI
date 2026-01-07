# -*- coding: utf-8 -*-
"""
MyLedger Data Migration Tool: SQLite -> Supabase (PostgreSQL)
"""
import sys
import os

# 确保能导入 src 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, Snapshot, Transfer, PriceHistory

def migrate():
    # 1. 配置本地数据库
    local_db_path = 'local_ledger.db'
    if not os.path.exists(local_db_path):
        print(f"❌ 错误: 在当前目录下未找到 {local_db_path}")
        return

    local_engine = create_engine(f'sqlite:///{local_db_path}')
    LocalSession = sessionmaker(bind=local_engine)
    
    # 2. 获取远程数据库地址
    print("--- 🚀 MyLedger 数据一键搬家 ---")
    remote_url = input("请输入您的 Supabase DB_URL (即您填在 Secrets 里的那个): ").strip()
    
    if not remote_url:
        print("❌ 错误: 未提供有效的连接地址")
        return

    # 兼容处理
    if remote_url.startswith("postgresql://") and "postgresql+psycopg2://" not in remote_url:
        remote_url = remote_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "sslmode" not in remote_url:
        separator = "&" if "?" in remote_url else "?"
        remote_url += f"{separator}sslmode=require"

    try:
        remote_engine = create_engine(remote_url)
        RemoteSession = sessionmaker(bind=remote_engine)
        
        # 3. 开始迁移
        local_session = LocalSession()
        remote_session = RemoteSession()

        print("\n正在同步数据，请稍候...")

        # 迁移 Snapshots
        snapshots = local_session.query(Snapshot).all()
        print(f"📦 正在迁移快照记录: {len(snapshots)} 条...")
        for s in snapshots:
            # 清除 ID 让远程数据库自动重新分配
            new_s = Snapshot(date=s.date, account_name=s.account_name, symbol=s.symbol, quantity=s.quantity, created_at=s.created_at)
            remote_session.add(new_s)
        
        # 迁移 Transfers
        transfers = local_session.query(Transfer).all()
        print(f"💸 正在迁移转账记录: {len(transfers)} 条...")
        for t in transfers:
            new_t = Transfer(date=t.date, type=t.type, amount_usd=t.amount_usd, note=t.note, created_at=t.created_at)
            remote_session.add(new_t)

        # 迁移 PriceHistory
        prices = local_session.query(PriceHistory).all()
        print(f"📈 正在迁移价格历史: {len(prices)} 条...")
        for p in prices:
            new_p = PriceHistory(date=p.date, symbol=p.symbol, price_usd=p.price_usd, source=p.source, created_at=p.created_at)
            remote_session.add(new_p)

        # 提交到云端
        remote_session.commit()
        print("\n✅ 恭喜！数据同步成功。")
        print("现在刷新您的云端 Streamlit 页面，数据应该已经全都在那了。")

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
    finally:
        local_session.close()
        remote_session.close()

if __name__ == "__main__":
    migrate()
