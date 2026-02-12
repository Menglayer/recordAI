"""
Smart Price Update Tool
"""
import sys
sys.path.insert(0, '..')
from src.models import get_engine, Snapshot, PriceHistory
from src.database import session_scope
from datetime import date, datetime
from sqlalchemy import and_
from src import price_service

def update_prices_smart():
    """智能价格更新：自动拉取 + 手动补充"""
    
    print("=" * 60)
    print("💰 智能价格更新工具")
    print("=" * 60)
    
    engine = get_engine()
    
    # 1. 获取快照中的所有资产
    with session_scope(engine) as session:
        snapshots = session.query(Snapshot.symbol).distinct().all()
        symbols = sorted([s[0] for s in snapshots])
    
    if not symbols:
        print("\n❌ 没有找到快照记录")
        print("   请先使用 Streamlit 录入快照数据")
        return
    
    print(f"\n📋 从快照中找到 {len(symbols)} 个资产:")
    for i, sym in enumerate(symbols, 1):
        print(f"   {i}. {sym}")
    
    # 2. 自动拉取价格
    print(f"\n🚀 开始自动拉取价格...")
    print("-" * 60)
    
    service = price_service.PriceService()
    failed_symbols = []
    success_prices = {}
    
    for symbol in symbols:
        try:
            price = service.fetch_price(symbol)
            if price and price > 0:
                success_prices[symbol] = price
            else:
                failed_symbols.append(symbol)
        except Exception as e:
            print(f"❌ {symbol}: 获取失败 ({str(e)[:50]}...)")
            failed_symbols.append(symbol)
    
    print("-" * 60)
    print(f"\n✅ 成功: {len(success_prices)}/{len(symbols)} 个资产")
    
    if success_prices:
        print("\n成功获取的价格:")
        for sym, price in success_prices.items():
            print(f"  {sym:10s} -> ${price:>12,.2f}")
    
    # 3. 处理失败的资产
    if failed_symbols:
        print(f"\n⚠️  {len(failed_symbols)} 个资产获取失败:")
        for sym in failed_symbols:
            print(f"  - {sym}")
        
        print("\n是否手动输入这些资产的价格？")
        choice = input("(y/n): ").strip().lower()
        
        if choice == 'y':
            for symbol in failed_symbols:
                print(f"\n输入 {symbol} 的价格:")
                price_str = input(f"  ${symbol} = $").strip()
                
                if price_str:
                    try:
                        price = float(price_str)
                        if price > 0:
                            success_prices[symbol] = price
                            print(f"  ✅ 已记录 {symbol} = ${price:,.2f}")
                        else:
                            print(f"  ❌ 价格必须大于 0，跳过")
                    except ValueError:
                        print(f"  ❌ 无效格式，跳过")
                else:
                    print(f"  ⏭️  跳过")
    
    # 4. 保存所有价格到数据库
    if success_prices:
        print(f"\n💾 保存 {len(success_prices)} 个价格到数据库...")
        
        price_date = date.today()
        saved_count = 0
        
        with session_scope(engine) as session:
            for symbol, price in success_prices.items():
                try:
                    # 检查是否已存在
                    existing = session.query(PriceHistory).filter(
                        and_(
                            PriceHistory.date == price_date,
                            PriceHistory.symbol == symbol
                        )
                    ).first()
                    
                    if existing:
                        existing.price_usd = price
                        existing.source = 'manual' if symbol in failed_symbols else 'auto'
                        existing.created_at = datetime.utcnow()
                    else:
                        new_price = PriceHistory(
                            date=price_date,
                            symbol=symbol,
                            price_usd=price,
                            source='manual' if symbol in failed_symbols else 'auto'
                        )
                        session.add(new_price)
                    
                    saved_count += 1
                    
                except Exception as e:
                    print(f"  ❌ {symbol} 保存失败: {e}")
        
        print(f"✅ 成功保存 {saved_count} 个价格！")
    
    else:
        print("\n⚠️  没有价格可以保存")
    
    print("\n" + "=" * 60)
    print("💡 提示：")
    print("   1. 价格已保存到数据库")
    print("   2. 现在可以打开 Streamlit 查看仪表盘")
    print("   3. 运行: streamlit run app.py")
    print("=" * 60)


if __name__ == '__main__':
    update_prices_smart()
