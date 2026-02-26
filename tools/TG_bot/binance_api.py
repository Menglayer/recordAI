"""
Binance API 交互层
RSA 签名、余额查询、K线获取等底层 API 封装
"""
import os
import time
import base64
import logging
import requests
from urllib.parse import urlencode

from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

# ================= 配置 =================
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY', '').strip()
PRIVATE_KEY_B64 = os.environ.get('PRIVATE_KEY_BASE64', '').strip()

BASE_URL_SPOT = 'https://api.binance.com'
BASE_URL_FUTURES = 'https://fapi.binance.com'

# 共享 HTTP 会话
_session = requests.Session()


# ================= RSA 签名 =================

def load_private_key():
    """加载 RSA 私钥"""
    try:
        if not PRIVATE_KEY_B64:
            return None
        clean_key = PRIVATE_KEY_B64.replace('\\n', '\n').strip()
        key_bytes = base64.b64decode(clean_key)
        return serialization.load_pem_private_key(key_bytes, password=None)
    except Exception as e:
        logger.error(f"Private Key Load Error: {e}")
        return None


def send_signed_request(method, endpoint, params=None):
    """
    发送带 RSA 签名的 Binance API 请求
    
    Args:
        method: HTTP 方法 ('GET' 或 'POST')
        endpoint: API 路径
        params: 请求参数
        
    Returns:
        dict 或 None
    """
    if not BINANCE_API_KEY or not PRIVATE_KEY_B64:
        return None
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 60000
    query_string = urlencode(params)
    private_key = load_private_key()
    if not private_key:
        return None
    try:
        signature = base64.b64encode(
            private_key.sign(query_string.encode('utf-8'))
        ).decode('utf-8')
    except Exception as e:
        logger.error(f"Signing Error: {e}")
        return None
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    url = f"{BASE_URL_SPOT}{endpoint}"
    try:
        full_params = params.copy()
        full_params['signature'] = signature
        if method.upper() == 'GET':
            response = _session.get(url, params=full_params, headers=headers, timeout=10)
        else:
            response = _session.post(url, data=full_params, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Network Error: {e}")
        return None


# ================= 数据获取 =================

def get_real_total_balance():
    """
    获取 [现货 + 理财] 总余额
    
    Returns:
        tuple: (btc_total, usdt_total, detail_dict) 或 None
    """
    if not BINANCE_API_KEY:
        return None
    spot_btc, spot_usdt = 0.0, 0.0
    s_res = send_signed_request('GET', '/api/v3/account')
    if s_res and 'balances' in s_res:
        for b in s_res['balances']:
            if b['asset'] == 'BTC':
                spot_btc = float(b['free']) + float(b['locked'])
            if b['asset'] == 'USDT':
                spot_usdt = float(b['free']) + float(b['locked'])

    earn_btc, earn_usdt = 0.0, 0.0
    for path in ['/sapi/v1/simple-earn/flexible/position', '/sapi/v1/simple-earn/locked/position']:
        res = send_signed_request('GET', path, {'limit': 100})
        items = []
        if isinstance(res, dict) and 'rows' in res:
            items = res['rows']
        elif isinstance(res, list):
            items = res
        for row in items:
            if row['asset'] == 'BTC':
                earn_btc += float(row['totalAmount'])
            if row['asset'] == 'USDT':
                earn_usdt += float(row['totalAmount'])

    return spot_btc + earn_btc, spot_usdt + earn_usdt, {
        'spot_btc': spot_btc, 'earn_btc': earn_btc,
        'spot_usdt': spot_usdt, 'earn_usdt': earn_usdt
    }


def get_earn_apr(asset='BTC'):
    """
    获取理财产品实时 APR (用于估算)
    
    Args:
        asset: 资产名称
        
    Returns:
        float: APR 值
    """
    try:
        res = send_signed_request('GET', '/sapi/v1/simple-earn/flexible/list', {
            'asset': asset, 'current': 1, 'size': 5
        })
        if res and 'rows' in res and res['rows']:
            return float(res['rows'][0]['latestAnnualPercentageRate'])
    except Exception as e:
        logger.error(f"APR Fetch Error: {e}")
    return 0.0


def get_fng_index():
    """
    获取恐慌贪婪指数
    
    Returns:
        tuple: (值, 分类描述)
    """
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=3)
        data = r.json()
        return int(data['data'][0]['value']), data['data'][0]['value_classification']
    except Exception:
        return 50, "Unknown"


def fetch_klines(symbol='BTCUSDT', interval='1d', limit=300):
    """
    获取 K 线数据
    
    Args:
        symbol: 交易对
        interval: K 线周期
        limit: 数据条数
        
    Returns:
        list[float]: 收盘价列表
    """
    res = _session.get(
        f"{BASE_URL_SPOT}/api/v3/klines",
        params={'symbol': symbol, 'interval': interval, 'limit': limit},
        timeout=10
    ).json()
    return [float(k[4]) for k in res]


def fetch_btc_price():
    """获取 BTC 实时价格"""
    url = f"{BASE_URL_SPOT}/api/v3/ticker/price?symbol=BTCUSDT"
    return float(_session.get(url, timeout=5).json()['price'])


def fetch_funding_rate(symbol='BTCUSDT'):
    """获取资金费率"""
    res = _session.get(
        f"{BASE_URL_FUTURES}/fapi/v1/premiumIndex?symbol={symbol}",
        timeout=5
    ).json()
    return float(res['lastFundingRate'])


def fetch_24h_change(symbol='BTCUSDT'):
    """获取 24 小时涨跌幅"""
    res = _session.get(
        f"{BASE_URL_SPOT}/api/v3/ticker/24hr?symbol={symbol}",
        timeout=5
    ).json()
    return float(res['priceChangePercent'])
