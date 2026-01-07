# 快速开始 - 价格获取功能使用指南

## 🚀 5 分钟快速上手

### 方法 1: 使用 Streamlit Web 界面 (推荐)

1. **启动应用**
   ```bash
   streamlit run app.py
   ```

2. **访问应用**
   
   浏览器打开: http://localhost:8501

3. **导航到价格页面**
   
   点击侧边栏 → `📈 记录价格`

4. **使用自动拉取功能**
   
   - 点击 `🤖 自动拉取` 标签页
   - 选择资产来源：
     - **从快照记录中获取**: 自动获取你已记录的所有资产
     - **手动输入资产列表**: 输入想要查询的资产（每行一个）

5. **拉取价格**
   
   - 点击 `🚀 开始拉取价格` 按钮
   - 等待获取完成（会显示实时进度）
   - 查看结果表格
   - 价格会自动保存到数据库（可取消勾选）

---

### 方法 2: 命令行直接调用

#### 测试价格获取（不保存）

```python
# test_price.py
from price_service import fetch_and_display_prices

# 定义要查询的资产
symbols = ['BTC', 'ETH', 'SOL', 'NVDA', 'MSTR', 'USDT']

# 获取并显示价格
fetch_and_display_prices(symbols)
```

运行：
```bash
python test_price.py
```

#### 获取价格并保存到数据库

```python
# update_prices.py
from price_service import update_price_history_db

# 定义要更新的资产
symbols = ['BTC', 'ETH', 'SOL', 'NVDA', 'MSTR', 'COIN', 'USDT', 'USDC']

# 获取价格并保存
count = update_price_history_db(symbols)
print(f"\n✅ 成功保存 {count} 条价格记录！")
```

运行：
```bash
python update_prices.py
```

---

## 📊 支持的资产示例

### 加密货币
```
BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, MATIC, 
LINK, UNI, ATOM, LTC, NEAR, APT, ARB, OP, SUI, TIA
```

### 美股
```
NVDA, AAPL, TSLA, MSFT, GOOGL, AMZN, META, MSTR, COIN, 
HOOD, PLTR, SOFI, BABA
```

### 稳定币
```
USDT, USDC, DAI, BUSD
```

---

## ✅ 实际使用案例

### 案例 1: 每日价格更新

创建 `daily_update.py`:

```python
from price_service import update_price_history_db
from datetime import date

# 你持有的所有资产
my_assets = [
    'BTC', 'ETH', 'SOL',      # 加密货币
    'NVDA', 'MSTR', 'COIN',   # 美股
    'USDT'                     # 稳定币
]

print(f"📅 {date.today()} 价格更新")
count = update_price_history_db(my_assets)
print(f"✅ 完成！更新了 {count} 个资产的价格")
```

### 案例 2: 批量查询并比较

```python
from price_service import PriceService

service = PriceService()

# 查询多个 AI 相关股票
ai_stocks = ['NVDA', 'AMD', 'MSFT', 'GOOGL', 'META']
prices = service.fetch_prices(ai_stocks)

print("\n🤖 AI 股票价格对比:")
for symbol, price in prices.items():
    if price:
        print(f"  {symbol:6s} -> ${price:>10,.2f}")
```

### 案例 3: 从数据库读取快照并更新价格

```python
from models import get_engine, get_session, Snapshot
from price_service import update_price_history_db

# 连接数据库
engine = get_engine()
session = get_session(engine)

# 获取所有不同的资产代码
snapshots = session.query(Snapshot.symbol).distinct().all()
symbols = [s.symbol for s in snapshots]
session.close()

print(f"📋 从快照中找到 {len(symbols)} 个资产: {', '.join(symbols)}")

# 更新这些资产的价格
if symbols:
    count = update_price_history_db(symbols)
    print(f"✅ 已更新 {count} 个资产的价格到数据库")
else:
    print("⚠️ 没有找到任何快照记录")
```

---

## 🎯 常见问题

### Q1: 某些资产获取失败怎么办？

**A**: 模块会自动重试 3 次，并尝试备用数据源。如果仍然失败：
- 检查资产代码是否正确
- 确认网络连接正常
- 对于加密货币，确认交易对存在（如 BTC/USDT）

### Q2: 价格多久更新一次？

**A**: 
- 每次手动触发拉取时实时获取
- 建议每天更新 1-2 次即可
- 可以在 Web 界面中快速更新所有资产

### Q3: 可以获取历史价格吗？

**A**: 
- 当前版本只支持获取当前/最新价格
- 历史价格回填功能在开发计划中

### Q4: 数据保存在哪里？

**A**: 
- 所有价格数据保存在本地 SQLite 数据库 `local_ledger.db`
- 在 `price_history` 表中
- 可以在 Web 界面的"数据管理"页面查看和导出

---

## 💡 最佳实践

1. **每日例行更新**: 每天晚上更新一次价格，用于计算当日净值
2. **快照后更新**: 每次记录资产快照后，立即更新价格
3. **定期备份**: 定期导出价格数据到 CSV 以防万一
4. **监控失败**: 如果某个资产经常获取失败，考虑手动输入或检查代码

---

## 🔗 相关文档

- [价格服务完整文档](PRICE_SERVICE_DOCS.md)
- [项目总结](PROJECT_SUMMARY.md)
- [README](README.md)

---

**提示**: 这个功能是完全本地运行的，API 调用都是免费的公开数据源，不需要任何密钥或账号！🎉
