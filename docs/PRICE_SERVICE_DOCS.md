# 价格服务模块文档

## 📊 概述

`price_service.py` 是 MyLedger 的核心价格获取模块，支持从多个数据源自动获取资产价格。

---

## 🎯 主要功能

### 1. 多数据源支持

| 资产类型 | 主要数据源 | 备用数据源 | 示例 |
|---------|-----------|-----------|------|
| **加密货币** | CCXT (Binance) | CoinGecko | BTC, ETH, SOL |
| **美股** | yfinance | - | NVDA, AAPL, TSLA |
| **稳定币** | 固定价格 1.0 | - | USDT, USDC |

### 2. 智能资产识别

模块会自动识别资产类型：
- 检测是否为稳定币（返回 1.0）
- 检测是否为常见加密货币（使用 CCXT）
- 其他资产视为股票（使用 yfinance）

### 3. 错误处理和重试

- 网络失败自动重试（默认 3 次）
- 主数据源失败自动切换到备用源
- API 限流保护（请求间隔延迟）

---

## 🔧 核心类和函数

### `PriceService` 类

主要价格获取服务类。

#### 初始化参数
```python
service = PriceService(retry_count=3, retry_delay=2)
```

- `retry_count`: 重试次数（默认 3）
- `retry_delay`: 重试延迟秒数（默认 2）

#### 主要方法

##### `fetch_price(symbol: str) -> Optional[float]`
获取单个资产的价格

```python
service = PriceService()
btc_price = service.fetch_price('BTC')  # 返回 BTC 的 USD 价格
```

##### `fetch_prices(symbols_list: List[str]) -> Dict[str, Optional[float]]`
批量获取多个资产的价格

```python
symbols = ['BTC', 'ETH', 'NVDA', 'USDT']
prices = service.fetch_prices(symbols)
# 返回: {'BTC': 93500.0, 'ETH': 3225.0, 'NVDA': 188.0, 'USDT': 1.0}
```

---

### 独立函数

##### `update_price_history_db(symbols_list: List[str], db_path='local_ledger.db')`
获取价格并保存到数据库（Upsert 操作）

```python
# 获取价格并保存到数据库
symbols = ['BTC', 'ETH', 'SOL']
count = update_price_history_db(symbols)
print(f"已保存 {count} 条记录")
```

**特性**：
- 如果当日已有记录，则更新价格
- 如果当日无记录，则插入新记录
- 自动记录价格来源（ccxt/yfinance/fixed）

##### `fetch_and_display_prices(symbols_list: List[str])`
获取价格并打印（仅用于测试，不保存）

```python
symbols = ['BTC', 'NVDA', 'USDT']
fetch_and_display_prices(symbols)
```

---

## 📝 使用示例

### 示例 1: 简单价格获取

```python
from price_service import PriceService

# 初始化服务
service = PriceService()

# 获取单个价格
btc_price = service.fetch_price('BTC')
print(f"BTC 价格: ${btc_price:,.2f}")
```

### 示例 2: 批量获取并保存

```python
from price_service import update_price_history_db

# 定义要获取的资产
symbols = ['BTC', 'ETH', 'SOL', 'NVDA', 'MSTR', 'USDT']

# 获取价格并保存到数据库
count = update_price_history_db(symbols)
print(f"成功保存 {count} 条价格记录")
```

### 示例 3: 从快照记录中获取价格

```python
from models import get_engine, get_session, Snapshot
from price_service import update_price_history_db

# 获取所有快照中的唯一资产
engine = get_engine()
session = get_session(engine)

snapshots = session.query(Snapshot.symbol).distinct().all()
symbols = [s.symbol for s in snapshots]

session.close()

# 更新这些资产的价格
update_price_history_db(symbols)
```

---

## 🖥️ Streamlit 集成

在 `app.py` 中已集成自动价格获取功能：

### 使用步骤

1. **打开应用**
   ```bash
   streamlit run app.py
   ```

2. **导航至价格页面**
   - 点击侧边栏 "📈 记录价格"

3. **选择"自动拉取"标签页**

4. **选择资产来源**
   - **从快照记录中获取**: 自动获取所有已记录快照的资产价格
   - **手动输入资产列表**: 手动输入资产代码（每行一个）

5. **点击"🚀 开始拉取价格"**

6. **查看结果**
   - 实时进度显示
   - 成功/失败状态
   - 成功率统计
   - 自动保存到数据库（可选）

---

## 🔍 支持的资产

### 加密货币（已预定义）
```
BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, ETC, BCH, NEAR, APT, ARB, OP, SUI, TIA, INJ, SEI, WLD, PEPE, SHIB, FET, RENDER, AGIX
```

### 稳定币
```
USDT, USDC, DAI, BUSD, TUSD, USDP, FDUSD
```

### 股票
任何在 Yahoo Finance 上市的股票（如 NVDA, AAPL, TSLA, MSTR, COIN 等）

---

## ⚠️ 注意事项

### API 限流
- CCXT (Binance): 建议每请求间隔 0.5-1 秒
- yfinance: 可能被限流，建议不要过于频繁请求
- CoinGecko (免费版): 每分钟有请求限制

### 数据准确性
- 加密货币价格为实时/近实时价格
- 股票价格可能有 15 分钟延迟（取决于数据源）
- 非交易时段可能获取不到最新价格

### 网络依赖
- 需要稳定的网络连接
- 部分地区可能需要代理访问某些 API
- 失败时会自动重试并切换数据源

---

## 🛠️ 故障排除

### 问题 1: 获取失败
**症状**: 所有资产都返回 None

**解决方案**:
1. 检查网络连接
2. 确认 API 服务是否可用
3. 检查是否被限流
4. 尝试增加重试次数和延迟

```python
service = PriceService(retry_count=5, retry_delay=5)
```

### 问题 2: 特定资产获取失败
**症状**: 某些资产无法获取价格

**解决方案**:
1. 检查资产代码是否正确
2. 确认该资产是否在数据源中存在
3. 对于加密货币，确认交易对是否存在（如 BTC/USDT）
4. 对于股票，确认股票代码是否正确

### 问题 3: 数据库保存失败
**症状**: 价格获取成功但无法保存

**解决方案**:
1. 检查数据库文件是否存在
2. 确认数据库连接正常
3. 查看错误日志获取详细信息

---

## 📈 性能优化建议

1. **批量获取**: 一次获取多个资产比分次获取更高效
2. **缓存价格**: 避免短时间内重复获取相同资产
3. **定时更新**: 使用定时任务定期更新价格（如每小时）
4. **异步处理**: 对于大量资产，可考虑使用异步方式

---

## 🔮 未来改进

- [ ] 支持更多数据源（如 CoinMarketCap, Dune Analytics）
- [ ] 异步批量获取以提高性能
- [ ] 历史价格回填功能
- [ ] 价格预警和通知
- [ ] 多币种支持（EUR, CNY 等）
- [ ] 定时任务自动更新

---

## 📄 许可证
MIT License

**创建日期**: 2026-01-06  
**版本**: v1.0.0
