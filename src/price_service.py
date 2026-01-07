"""
MyLedger - Price Service Module
"""
import time
from datetime import date, datetime
from typing import Dict, List, Optional
import yfinance as yf
import ccxt
from pycoingecko import CoinGeckoAPI
from .models import get_engine, get_session, PriceHistory
from sqlalchemy import and_


class PriceService:
    """价格获取服务类"""
    
    # 常见加密货币符号
    CRYPTO_SYMBOLS = {
        'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 
        'DOT', 'MATIC', 'LINK', 'UNI', 'ATOM', 'LTC', 'ETC', 'BCH',
        'NEAR', 'APT', 'ARB', 'OP', 'SUI', 'TIA', 'INJ', 'SEI',
        'WLD', 'PEPE', 'SHIB', 'FET', 'RENDER', 'AGIX'
    }
    
    # 稳定币（价格固定为 1.0）
    STABLECOINS = {'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'FDUSD'}
    
    def __init__(self, retry_count=3, retry_delay=2):
        """
        初始化价格服务
        
        Args:
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.binance = ccxt.binance()
        self.coingecko = CoinGeckoAPI()
        
    def _is_crypto(self, symbol: str) -> bool:
        """判断是否为加密货币"""
        return symbol.upper() in self.CRYPTO_SYMBOLS
    
    def _is_stablecoin(self, symbol: str) -> bool:
        """判断是否为稳定币"""
        return symbol.upper() in self.STABLECOINS
    
    def _fetch_crypto_price_ccxt(self, symbol: str) -> Optional[float]:
        """
        使用 CCXT 从 Binance 获取加密货币价格
        
        Args:
            symbol: 加密货币符号（如 BTC, ETH）
            
        Returns:
            价格（USDT），失败返回 None
        """
        try:
            trading_pair = f"{symbol.upper()}/USDT"
            ticker = self.binance.fetch_ticker(trading_pair)
            price = ticker['last']
            print(f"✓ [CCXT Binance] {symbol}: ${price:,.2f}")
            return float(price)
        except Exception as e:
            print(f"✗ [CCXT Binance] {symbol} 获取失败: {e}")
            return None
    
    def _fetch_crypto_price_coingecko(self, symbol: str) -> Optional[float]:
        """
        使用 CoinGecko 获取加密货币价格（备用）
        
        Args:
            symbol: 加密货币符号
            
        Returns:
            价格（USD），失败返回 None
        """
        try:
            # CoinGecko ID 映射（常见币种）
            symbol_to_id = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'BNB': 'binancecoin',
                'XRP': 'ripple',
                'ADA': 'cardano',
                'DOGE': 'dogecoin',
                'AVAX': 'avalanche-2',
                'DOT': 'polkadot',
                'MATIC': 'matic-network',
                'LINK': 'chainlink',
                'UNI': 'uniswap',
                'ATOM': 'cosmos',
                'LTC': 'litecoin',
            }
            
            coin_id = symbol_to_id.get(symbol.upper())
            if not coin_id:
                print(f"✗ [CoinGecko] {symbol} 未找到映射")
                return None
            
            data = self.coingecko.get_price(ids=coin_id, vs_currencies='usd')
            price = data[coin_id]['usd']
            print(f"✓ [CoinGecko] {symbol}: ${price:,.2f}")
            return float(price)
        except Exception as e:
            print(f"✗ [CoinGecko] {symbol} 获取失败: {e}")
            return None
    
    def _fetch_stock_price_yfinance(self, symbol: str) -> Optional[float]:
        """
        使用 yfinance 获取股票价格
        
        Args:
            symbol: 股票代码（如 NVDA, AAPL）
            
        Returns:
            价格（USD），失败返回 None
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            data = ticker.history(period='1d')
            
            if data.empty:
                print(f"✗ [yfinance] {symbol} 无数据")
                return None
            
            price = data['Close'].iloc[-1]
            print(f"✓ [yfinance] {symbol}: ${price:,.2f}")
            return float(price)
        except Exception as e:
            print(f"✗ [yfinance] {symbol} 获取失败: {e}")
            return None
    
    def fetch_price(self, symbol: str) -> Optional[float]:
        """
        获取单个资产的价格（带重试机制）
        
        Args:
            symbol: 资产符号
            
        Returns:
            价格（USD/USDT），失败返回 None
        """
        symbol = symbol.upper()
        
        # 稳定币直接返回 1.0
        if self._is_stablecoin(symbol):
            print(f"✓ [Stablecoin] {symbol}: $1.00")
            return 1.0
        
        # 加密货币：优先 CCXT，失败后尝试 CoinGecko
        if self._is_crypto(symbol):
            for attempt in range(self.retry_count):
                price = self._fetch_crypto_price_ccxt(symbol)
                if price is not None:
                    return price
                
                if attempt < self.retry_count - 1:
                    print(f"  ⟳ 重试 {attempt + 1}/{self.retry_count - 1}...")
                    time.sleep(self.retry_delay)
            
            # CCXT 失败，尝试 CoinGecko
            print(f"  → 尝试备用数据源 CoinGecko...")
            price = self._fetch_crypto_price_coingecko(symbol)
            if price is not None:
                return price
        
        # 股票：使用 yfinance
        else:
            for attempt in range(self.retry_count):
                price = self._fetch_stock_price_yfinance(symbol)
                if price is not None:
                    return price
                
                if attempt < self.retry_count - 1:
                    print(f"  ⟳ 重试 {attempt + 1}/{self.retry_count - 1}...")
                    time.sleep(self.retry_delay)
        
        print(f"✗ {symbol} 所有数据源均失败")
        return None
    
    def fetch_fx_rate(self, to_currency: str) -> float:
        """
        获取从 USD 到指定货币的汇率
        
        Args:
            to_currency: 目标货币代码 (如 CNY, EUR)
            
        Returns:
            汇率，失败返回 1.0 (保持 USD)
        """
        to_currency = to_currency.upper()
        if to_currency == 'USD':
            return 1.0
            
        try:
            # yfinance 汇率代码格式: USDCNY=X
            ticker = yf.Ticker(f"USD{to_currency}=X")
            data = ticker.history(period='1d')
            if not data.empty:
                rate = data['Close'].iloc[-1]
                print(f"✓ [FX] USD/{to_currency}: {rate:.4f}")
                return float(rate)
        except Exception as e:
            print(f"✗ [FX] {to_currency} 汇率获取失败: {e}")
            
        return 1.0

    def fetch_prices(self, symbols_list: List[str]) -> Dict[str, Optional[float]]:
        """
        批量获取多个资产的价格
        
        Args:
            symbols_list: 资产符号列表
            
        Returns:
            字典 {symbol: price}
        """
        print(f"\n📊 开始获取 {len(symbols_list)} 个资产的价格...")
        print("=" * 60)
        
        prices = {}
        for symbol in symbols_list:
            price = self.fetch_price(symbol)
            prices[symbol.upper()] = price
            time.sleep(0.5)  # 避免 API 限流
        
        print("=" * 60)
        success_count = sum(1 for p in prices.values() if p is not None)
        print(f"✅ 完成: {success_count}/{len(symbols_list)} 个资产获取成功\n")
        
        return prices


def update_price_history_db(symbols_list: List[str], db_path='local_ledger.db'):
    """
    获取价格并更新到数据库
    
    Args:
        symbols_list: 资产符号列表
        db_path: 数据库路径
        
    Returns:
        更新/插入的记录数
    """
    # 获取价格
    service = PriceService()
    prices = service.fetch_prices(symbols_list)
    
    # 连接数据库
    engine = get_engine(db_path)
    session = get_session(engine)
    
    today = date.today()
    updated_count = 0
    inserted_count = 0
    
    try:
        for symbol, price in prices.items():
            if price is None:
                print(f"⊘ {symbol}: 跳过（获取失败）")
                continue
            
            # 判断数据源
            if symbol in service.STABLECOINS:
                source = 'fixed'
            elif symbol in service.CRYPTO_SYMBOLS:
                source = 'ccxt'
            else:
                source = 'yfinance'
            
            # 检查今天是否已有记录
            existing = session.query(PriceHistory).filter(
                and_(
                    PriceHistory.date == today,
                    PriceHistory.symbol == symbol
                )
            ).first()
            
            if existing:
                # 更新现有记录
                existing.price_usd = price
                existing.source = source
                existing.created_at = datetime.utcnow()
                updated_count += 1
                print(f"⟳ {symbol}: 更新价格 ${price:,.2f}")
            else:
                # 插入新记录
                new_price = PriceHistory(
                    date=today,
                    symbol=symbol,
                    price_usd=price,
                    source=source
                )
                session.add(new_price)
                inserted_count += 1
                print(f"+ {symbol}: 新增价格 ${price:,.2f}")
        
        session.commit()
        
        print("\n" + "=" * 60)
        print(f"💾 数据库更新完成:")
        print(f"  - 新增: {inserted_count} 条")
        print(f"  - 更新: {updated_count} 条")
        print("=" * 60 + "\n")
        
        return inserted_count + updated_count
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 数据库更新失败: {e}\n")
        raise
    finally:
        session.close()


def fetch_and_display_prices(symbols_list: List[str]):
    """
    获取价格并打印（不保存到数据库）
    用于测试
    
    Args:
        symbols_list: 资产符号列表
    """
    service = PriceService()
    prices = service.fetch_prices(symbols_list)
    
    print("\n" + "=" * 60)
    print("📋 价格汇总:")
    print("=" * 60)
    
    for symbol, price in prices.items():
        if price is not None:
            print(f"  {symbol:8s} -> ${price:>12,.2f}")
        else:
            print(f"  {symbol:8s} -> 获取失败")
    
    print("=" * 60 + "\n")


# 测试代码
if __name__ == '__main__':
    # 测试 1: 获取价格（不保存）
    test_symbols = ['BTC', 'ETH', 'SOL', 'USDT', 'NVDA', 'MSTR', 'COIN']
    
    print("🧪 测试 1: 获取价格（不保存到数据库）")
    fetch_and_display_prices(test_symbols)
    
    # 测试 2: 获取价格并保存到数据库
    print("\n🧪 测试 2: 获取价格并保存到数据库")
    user_input = input("是否要将价格保存到数据库？(y/N): ")
    
    if user_input.lower() == 'y':
        update_price_history_db(test_symbols)
        print("✅ 测试完成！")
    else:
        print("❌ 已取消保存")
