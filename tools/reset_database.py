"""
Database Reset Tool
"""
import sys
sys.path.insert(0, '..')
from src.models import get_engine, Snapshot, Transfer, PriceHistory
from src.database import session_scope

def reset_database():
    """清空所有表的数据"""
    
    print("=" * 60)
    print("⚠️  数据库重置工具")
    print("=" * 60)
    print("\n此操作将删除以下数据：")
    print("  - 所有快照记录 (snapshots)")
    print("  - 所有转账记录 (transfers)")
    print("  - 所有价格记录 (price_history)")
    print("\n⚠️  警告：此操作不可恢复！\n")
    
    # 确认操作
    confirm = input("请输入 'DELETE' 确认删除所有数据: ")
    
    if confirm != 'DELETE':
        print("\n❌ 操作已取消")
        return
    
    # 二次确认
    confirm2 = input("\n请再次确认，输入 'YES' 继续: ")
    
    if confirm2 != 'YES':
        print("\n❌ 操作已取消")
        return
    
    # 执行删除
    engine = get_engine('local_ledger.db')
    
    try:
        with session_scope(engine) as session:
            # 统计删除前的数据量
            snapshot_count = session.query(Snapshot).count()
            transfer_count = session.query(Transfer).count()
            price_count = session.query(PriceHistory).count()
            
            print("\n🔄 正在删除数据...")
            
            # 删除所有记录
            session.query(Snapshot).delete()
            session.query(Transfer).delete()
            session.query(PriceHistory).delete()
        
        print("\n✅ 数据库已清空！")
        print(f"\n删除统计:")
        print(f"  - 快照记录: {snapshot_count} 条")
        print(f"  - 转账记录: {transfer_count} 条")
        print(f"  - 价格记录: {price_count} 条")
        print("\n" + "=" * 60)
        print("💡 提示：现在可以开始录入您的真实数据了")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 删除失败: {e}")


if __name__ == '__main__':
    reset_database()
