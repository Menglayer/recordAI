"""
MyLedger - 数据库初始化脚本
运行此脚本创建 SQLite 数据库和所有表
"""
import os
from models import Base, get_engine, Snapshot, Transfer, PriceHistory
from datetime import date


def init_database(db_path='local_ledger.db'):
    """
    初始化数据库并创建所有表
    
    Args:
        db_path: 数据库文件路径，默认为 'local_ledger.db'
    """
    # 检查数据库是否已存在
    db_exists = os.path.exists(db_path)
    
    if db_exists:
        print(f"⚠️  数据库文件 '{db_path}' 已存在")
        user_input = input("是否要重新创建？这将删除所有现有数据 (y/N): ")
        
        if user_input.lower() != 'y':
            print("❌ 操作已取消")
            return
        
        # 删除旧数据库
        os.remove(db_path)
        print(f"🗑️  已删除旧数据库文件")
    
    # 创建引擎
    engine = get_engine(db_path)
    
    # 创建所有表
    print(f"📊 正在创建数据库表...")
    Base.metadata.create_all(engine)
    
    print(f"✅ 数据库初始化成功！")
    print(f"\n创建的表:")
    print(f"  1. snapshots      - 资产快照表")
    print(f"  2. transfers      - 资金流水表")
    print(f"  3. price_history  - 价格历史表")
    print(f"\n数据库文件: {os.path.abspath(db_path)}")
    
    # 显示表结构
    print("\n" + "="*60)
    print("表结构预览:")
    print("="*60)
    
    print("\n📸 snapshots (资产快照)")
    print("  - id: 主键")
    print("  - date: 快照日期")
    print("  - account_name: 账户名称 (如: Binance, OKX)")
    print("  - symbol: 资产代码 (如: BTC, ETH, AAPL)")
    print("  - quantity: 持仓数量")
    print("  - created_at: 记录创建时间")
    
    print("\n💰 transfers (资金流水)")
    print("  - id: 主键")
    print("  - date: 转账日期")
    print("  - type: 类型 (deposit/withdrawal)")
    print("  - amount_usd: 金额（美元）")
    print("  - note: 备注")
    print("  - created_at: 记录创建时间")
    
    print("\n📈 price_history (价格历史)")
    print("  - id: 主键")
    print("  - date: 价格日期")
    print("  - symbol: 资产代码")
    print("  - price_usd: 价格（美元）")
    print("  - source: 价格来源")
    print("  - created_at: 记录创建时间")
    
    return engine


def add_sample_data(engine):
    """添加示例数据（可选）"""
    from models import get_session
    from datetime import date, timedelta
    
    session = get_session(engine)
    
    try:
        # 示例快照数据
        today = date.today()
        sample_snapshots = [
            Snapshot(date=today, account_name='Binance', symbol='BTC', quantity=0.5),
            Snapshot(date=today, account_name='Binance', symbol='ETH', quantity=5.0),
            Snapshot(date=today, account_name='OKX', symbol='USDT', quantity=10000.0),
        ]
        
        # 示例转账记录
        sample_transfers = [
            Transfer(date=today - timedelta(days=30), type='deposit', amount_usd=10000.0, note='初始入金'),
            Transfer(date=today - timedelta(days=10), type='deposit', amount_usd=5000.0, note='追加投资'),
        ]
        
        # 示例价格数据
        sample_prices = [
            PriceHistory(date=today, symbol='BTC', price_usd=95000.0, source='yfinance'),
            PriceHistory(date=today, symbol='ETH', price_usd=3500.0, source='yfinance'),
            PriceHistory(date=today, symbol='USDT', price_usd=1.0, source='coingecko'),
        ]
        
        session.add_all(sample_snapshots + sample_transfers + sample_prices)
        session.commit()
        
        print("\n✅ 已添加示例数据")
        print(f"  - {len(sample_snapshots)} 条快照记录")
        print(f"  - {len(sample_transfers)} 条转账记录")
        print(f"  - {len(sample_prices)} 条价格记录")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 添加示例数据失败: {e}")
    finally:
        session.close()


if __name__ == '__main__':
    print("="*60)
    print("MyLedger - 数据库初始化工具")
    print("="*60)
    print()
    
    # 初始化数据库
    engine = init_database()
    
    if engine:
        print("\n" + "="*60)
        add_sample = input("\n是否添加示例数据？(y/N): ")
        
        if add_sample.lower() == 'y':
            add_sample_data(engine)
        
        print("\n" + "="*60)
        print("🎉 数据库准备完成！")
        print("💡 下一步: 运行 'streamlit run app.py' 启动应用")
        print("="*60)
