"""
Data Diagnostic Tool
"""
import sys
sys.path.insert(0, '..')
from src.models import get_engine, get_session, Snapshot, Transfer, PriceHistory
from datetime import date

def diagnose_data():
    """诊断数据问题"""
    engine = get_engine('local_ledger.db')
    session = get_session(engine)
    
    print("=" * 60)
    print("🔍 MyLedger 数据诊断工具")
    print("=" * 60)
    print()
    
    try:
        # 1. 检查快照数据
        print("📸 检查快照数据...")
        snapshots = session.query(Snapshot).all()
        
        if not snapshots:
            print("❌ 没有快照数据！")
            print("   请前往「数据录入」页面添加快照")
            return
        
        print(f"✅ 找到 {len(snapshots)} 条快照记录")
        
        # 按日期分组
        dates = set(s.date for s in snapshots)
        print(f"\n快照日期: {sorted(dates)}")
        
        # 显示资产列表
        symbols = set(s.symbol for s in snapshots)
        print(f"资产列表: {sorted(symbols)}")
        
        # 显示详细快照
        print("\n快照详情:")
        for s in snapshots:
            print(f"  {s.date} | {s.account_name:15s} | {s.symbol:10s} | {s.quantity:>15,.8f}".rstrip('0').rstrip('.'))
        
        print("\n" + "-" * 60)
        
        # 2. 检查价格数据
        print("\n💰 检查价格数据...")
        prices = session.query(PriceHistory).all()
        
        if not prices:
            print("❌ 没有价格数据！这就是为什么净值计算不出来的原因！")
            print("\n解决方案:")
            print("   1. 前往「记录价格」页面")
            print("   2. 点击「自动拉取」标签")
            print("   3. 选择「从快照记录中获取」")
            print("   4. 点击「🚀 开始拉取价格」按钮")
            print("\n或者手动输入价格:")
            for symbol in sorted(symbols):
                print(f"   - {symbol}: 输入当前价格")
            return
        
        print(f"✅ 找到 {len(prices)} 条价格记录")
        
        # 按日期分组价格
        price_dates = set(p.date for p in prices)
        print(f"\n价格日期: {sorted(price_dates)}")
        
        # 显示价格列表
        price_symbols = set(p.symbol for p in prices)
        print(f"有价格的资产: {sorted(price_symbols)}")
        
        print("\n价格详情:")
        for p in sorted(prices, key=lambda x: (x.date, x.symbol)):
            print(f"  {p.date} | {p.symbol:10s} | ${p.price_usd:>12,.2f} | 来源: {p.source or 'manual'}")
        
        print("\n" + "-" * 60)
        
        # 3. 检查匹配情况
        print("\n🔍 检查价格匹配...")
        
        missing_prices = []
        for s in snapshots:
            # 检查是否有对应的价格
            has_price = any(
                p.symbol == s.symbol and p.date <= s.date 
                for p in prices
            )
            
            if not has_price:
                missing_prices.append((s.date, s.symbol))
        
        if missing_prices:
            print(f"❌ 发现 {len(missing_prices)} 个资产缺少价格数据：")
            for snap_date, symbol in sorted(set(missing_prices)):
                print(f"   - {snap_date} | {symbol}")
            print("\n解决方案:")
            print("   请为这些资产更新价格（自动拉取或手动输入）")
        else:
            print("✅ 所有资产都有价格数据！")
        
        print("\n" + "-" * 60)
        
        # 4. 检查转账数据
        print("\n💸 检查转账数据...")
        transfers = session.query(Transfer).all()
        
        if not transfers:
            print("⚠️  没有转账记录")
            print("   建议：添加初始入金记录以准确计算收益率")
        else:
            print(f"✅ 找到 {len(transfers)} 条转账记录")
            
            total_deposits = sum(t.amount_usd for t in transfers if t.type == 'deposit')
            total_withdrawals = sum(t.amount_usd for t in transfers if t.type == 'withdrawal')
            
            print(f"\n转账汇总:")
            print(f"  总入金: ${total_deposits:,.2f}")
            print(f"  总出金: ${total_withdrawals:,.2f}")
            print(f"  净投入: ${total_deposits - total_withdrawals:,.2f}")
        
        print("\n" + "=" * 60)
        print("诊断完成！")
        print("=" * 60)
        
    finally:
        session.close()


if __name__ == '__main__':
    diagnose_data()
