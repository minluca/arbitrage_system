# Exchange Integration Guide

This document provides detailed technical specifications for each supported cryptocurrency exchange, including API endpoints, WebSocket protocols, and parsing logic.

---

## Table of Contents

1. [Binance](#1-binance)
2. [OKX](#2-okx)
3. [Bybit](#3-bybit)
4. [Adding New Exchanges](#4-adding-new-exchanges)
5. [API Reference Summary](#5-api-reference-summary)

---

## 1. Binance

### 1.1 Overview

- **Base URL (REST)**: `https://api.binance.com`
- **WebSocket URL**: `wss://stream.binance.com:9443/stream`
- **Documentation**: <https://binance-docs.github.io/apidocs/spot/en/>
- **Implementation**: [python/data_sources/binance_exchange.py](../python/data_sources/binance_exchange.py)

### 1.2 REST API

#### Binance: Fetch Symbols

**Endpoint**: `GET /api/v3/exchangeInfo`

**Purpose**: Retrieve all available trading pairs on Binance Spot market.

**Response Format**:

```json
{
  "symbols": [
    {
      "symbol": "BTCUSDT",
      "status": "TRADING",
      "baseAsset": "BTC",
      "quoteAsset": "USDT"
    }
  ]
}
```

**Filtering**: Only pairs with `status == "TRADING"` are selected.

**Code**:

```python
async def fetch_symbols(self, client):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    resp = await client.get(url)
    data = resp.json()
    symbols = {item['symbol'] for item in data['symbols'] if item.get('status') == 'TRADING'}
    return symbols
```

#### Binance: Fetch Initial Prices

**Endpoint**: `GET /api/v3/ticker/24hr`

**Purpose**: Retrieve 24-hour price and volume statistics for all trading pairs.

**Response Format**:

```json
[
  {
    "symbol": "BTCUSDT",
    "lastPrice": "50000.00",
    "volume": "12345.67"
  }
]
```

**Extracted Fields**:

- `symbol`: Trading pair symbol
- `lastPrice`: Most recent trade price
- `volume`: 24-hour trading volume (base asset)

**Code**:

```python
async def fetch_initial_prices(self, client, valid_pairs):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    resp = await client.get(url)
    data = resp.json()
    snapshot = []
    for item in data:
        if item['symbol'] in valid_pairs:
            snapshot.append({
                CSV_FIELDS[0]: now_ts(),
                CSV_FIELDS[1]: item['symbol'],
                CSV_FIELDS[4]: float(item['lastPrice']),
                CSV_FIELDS[5]: float(item['volume']),
                CSV_FIELDS[6]: 'Binance',
            })
    return snapshot
```

### 1.3 WebSocket API

#### Binance: Connection

**URL Format**:

```plaintext
wss://stream.binance.com:9443/stream?streams={stream1}/{stream2}/...
```

**Stream Format**: `{symbol}@ticker` (lowercase)

**Example**:

```plaintext
wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker
```

**Connection Parameters**:

- `ping_interval`: 20 seconds
- `ping_timeout`: 20 seconds
- `max_size`: None (unlimited message size)

#### Binance: Message Format

**Ticker Update**:

```json
{
  "stream": "btcusdt@ticker",
  "data": {
    "s": "BTCUSDT",
    "c": "50000.00",
    "v": "12345.67"
  }
}
```

**Relevant Fields**:

- `data.s`: Symbol
- `data.c`: Close price (last price)
- `data.v`: Volume

#### Binance: Parser Implementation

**Location**: [python/data_sources/parsers.py](../python/data_sources/parsers.py)

**Function**: `parse_binance(msg)`

```python
def parse_binance(msg):
    data = msg.get("data", msg)
    try:
        symbol = norm_symbol(data["s"])
        base, quote = split_symbol(symbol)
        return {
            CSV_FIELDS[0]: now_ts(),
            CSV_FIELDS[1]: norm_symbol(data["s"]),
            CSV_FIELDS[2]: base,
            CSV_FIELDS[3]: quote,
            CSV_FIELDS[4]: float(data["c"]),
            CSV_FIELDS[5]: float(data["v"]),
            CSV_FIELDS[6]: "Binance"
        }
    except Exception:
        return None
```

---

## 2. OKX

### 2.1 Overview

- **Base URL (REST)**: `https://www.okx.com`
- **WebSocket URL**: `wss://ws.okx.com:8443/ws/v5/public`
- **Documentation**: <https://www.okx.com/docs-v5/en/>
- **Implementation**: [python/data_sources/okx_exchange.py](../python/data_sources/okx_exchange.py)

### 2.2 REST API

#### OKX: Fetch Symbols

**Endpoint**: `GET /api/v5/public/instruments?instType=SPOT`

**Purpose**: Retrieve all SPOT trading instruments.

**Response Format**:

```json
{
  "data": [
    {
      "instId": "BTC-USDT",
      "state": "live",
      "baseCcy": "BTC",
      "quoteCcy": "USDT"
    }
  ]
}
```

**Filtering**: Only instruments with `state == "live"` are selected.

**Symbol Normalization**: `BTC-USDT` → `BTCUSDT` (remove hyphen)

**Code**:

```python
async def fetch_symbols(self, client):
    url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
    resp = await client.get(url)
    data = resp.json()
    symbols = {item['instId'].replace("-", "") for item in data['data'] if item.get('state') == 'live'}
    return symbols
```

#### OKX: Fetch Initial Prices

**Endpoint**: `GET /api/v5/market/tickers?instType=SPOT`

**Purpose**: Retrieve current ticker data for all SPOT instruments.

**Response Format**:

```json
{
  "data": [
    {
      "instId": "BTC-USDT",
      "last": "50000.00",
      "vol24h": "12345.67"
    }
  ]
}
```

**Extracted Fields**:

- `instId`: Instrument ID (with hyphen)
- `last`: Last traded price
- `vol24h`: 24-hour trading volume

### 2.3 WebSocket API

#### OKX: Connection

**URL**: `wss://ws.okx.com:8443/ws/v5/public`

**Subscription Required**: Yes (send subscription message after connection)

**Subscription Format**:

```json
{
  "op": "subscribe",
  "args": [
    {"channel": "tickers", "instId": "BTC-USDT"},
    {"channel": "tickers", "instId": "ETH-USDT"}
  ]
}
```

**Note**: OKX uses hyphenated format (`BTC-USDT`), so use `to_okx_format()` helper

#### OKX: Message Format

**Ticker Update**:

```json
{
  "arg": {"channel": "tickers", "instId": "BTC-USDT"},
  "data": [
    {
      "instId": "BTC-USDT",
      "last": "50000.00",
      "vol24h": "12345.67"
    }
  ]
}
```

#### OKX: Parser Implementation

**Function**: `parse_okx(msg)`

```python
def parse_okx(msg):
    if "data" not in msg:
        return None
    try:
        item = msg["data"][0]
        symbol = norm_symbol(item["instId"])
        base, quote = split_symbol(symbol)
        return {
            CSV_FIELDS[0]: now_ts(),
            CSV_FIELDS[1]: norm_symbol(item["instId"]),
            CSV_FIELDS[2]: base,
            CSV_FIELDS[3]: quote,
            CSV_FIELDS[4]: float(item["last"]),
            CSV_FIELDS[5]: float(item["vol24h"]),
            CSV_FIELDS[6]: "OKX"
        }
    except Exception:
        return None
```

**Helper Function**: `to_okx_format()`

```python
def to_okx_format(s: str) -> str:
    # BTCUSDT -> BTC-USDT
    if s.endswith(("USDT", "USDC", "TUSD")):
        return s[:-4] + "-" + s[-4:]
    else:
        return s[:-3] + "-" + s[-3:]
```

---

## 3. Bybit

### 3.1 Overview

- **Base URL (REST)**: `https://api.bybit.com`
- **WebSocket URL**: `wss://stream.bybit.com/v5/public/spot`
- **Documentation**: <https://bybit-exchange.github.io/docs/v5/intro>
- **Implementation**: [python/data_sources/bybit_exchange.py](../python/data_sources/bybit_exchange.py)

### 3.2 REST API

#### Bybit: Fetch Symbols

**Endpoint**: `GET /v5/market/instruments-info?category=spot`

**Purpose**: Retrieve all SPOT trading instruments.

**Response Format**:

```json
{
  "result": {
    "list": [
      {
        "symbol": "BTCUSDT",
        "status": "Trading",
        "baseCoin": "BTC",
        "quoteCoin": "USDT"
      }
    ]
  }
}
```

**Filtering**: Only instruments with `status == "Trading"` are selected.

**Code**:

```python
async def fetch_symbols(self, client):
    url = "https://api.bybit.com/v5/market/instruments-info?category=spot"
    resp = await client.get(url)
    data = resp.json()
    symbols = {item['symbol'] for item in data['result']['list'] if item.get('status') == 'Trading'}
    return symbols
```

#### Bybit: Fetch Initial Prices

**Endpoint**: `GET /v5/market/tickers?category=spot`

**Purpose**: Retrieve current ticker data for all SPOT instruments.

**Response Format**:

```json
{
  "result": {
    "list": [
      {
        "symbol": "BTCUSDT",
        "lastPrice": "50000.00",
        "volume24h": "12345.67"
      }
    ]
  }
}
```

**Extracted Fields**:

- `symbol`: Trading pair symbol
- `lastPrice`: Last traded price
- `volume24h`: 24-hour trading volume

### 3.3 WebSocket API

#### Bybit: Connection

**URL**: `wss://stream.bybit.com/v5/public/spot`

**Subscription Required**: Yes

**Important Limitation**: **Maximum 10 tickers per subscription message**

**Subscription Format**:

```json
{
  "op": "subscribe",
  "args": [
    "tickers.BTCUSDT",
    "tickers.ETHUSDT",
    ...up to 10 total
  ]
}
```

**Batching Strategy**:

For 44 symbols, split into 5 batches:

```python
ticker_args = [f"tickers.{s}" for s in symbols]
batch_size = 10
sub_messages = []
for i in range(0, len(ticker_args), batch_size):
    batch = ticker_args[i:i+batch_size]
    sub_messages.append({
        "op": "subscribe",
        "args": batch
    })

# Send each batch with small delay
for sub_msg in sub_messages:
    await ws.send(json.dumps(sub_msg))
    await asyncio.sleep(0.1)
```

#### Bybit: Subscription Response

**Success**:

```json
{
  "success": true,
  "ret_msg": "",
  "conn_id": "...",
  "op": "subscribe"
}
```

**Failure** (too many tickers):

```json
{
  "success": false,
  "ret_msg": "args size >10",
  "conn_id": "...",
  "op": "subscribe"
}
```

#### Bybit: Message Format

**Ticker Update**:

```json
{
  "topic": "tickers.BTCUSDT",
  "type": "snapshot",
  "data": {
    "symbol": "BTCUSDT",
    "lastPrice": "50000.00",
    "volume24h": "12345.67"
  }
}
```

**Topic Format**: `tickers.{SYMBOL}` (not just `tickers`)

#### Bybit: Parser Implementation

**Function**: `parse_bybit(msg)`

```python
def parse_bybit(msg):
    topic = msg.get('topic', '')
    if not topic.startswith('tickers.') or 'data' not in msg:
        return None
    try:
        data = msg['data']
        symbol = norm_symbol(data['symbol'])
        base, quote = split_symbol(symbol)
        return {
            CSV_FIELDS[0]: now_ts(),
            CSV_FIELDS[1]: symbol,
            CSV_FIELDS[2]: base,
            CSV_FIELDS[3]: quote,
            CSV_FIELDS[4]: float(data['lastPrice']),
            CSV_FIELDS[5]: float(data['volume24h']),
            CSV_FIELDS[6]: "Bybit"
        }
    except Exception:
        return None
```

---

## 4. Adding New Exchanges

### 4.1 Required Steps

To add a new exchange (e.g., Kraken, Coinbase), follow these steps:

#### Step 1: Create Exchange Class

Create `python/data_sources/{exchange}_exchange.py` implementing `ExchangeBase`:

```python
from .exchange_base import ExchangeBase
from config.settings import CSV_FIELDS
from core.utils import now_ts
from data_sources.parsers import parse_{exchange}

class {Exchange}Exchange(ExchangeBase):
    async def fetch_symbols(self, client):
        # Implement REST API call to get trading pairs
        pass

    async def fetch_initial_prices(self, client, valid_pairs):
        # Implement REST API call to get initial snapshot
        pass

    async def stream_ws(self, updates_q, symbols):
        # Implement WebSocket connection and streaming
        pass
```

#### Step 2: Create Parser Function

Add to `python/data_sources/parsers.py`:

```python
def parse_{exchange}(msg):
    # Extract relevant fields from WebSocket message
    try:
        return {
            CSV_FIELDS[0]: now_ts(),
            CSV_FIELDS[1]: symbol,
            CSV_FIELDS[2]: base,
            CSV_FIELDS[3]: quote,
            CSV_FIELDS[4]: float(price),
            CSV_FIELDS[5]: float(volume),
            CSV_FIELDS[6]: "{Exchange}"
        }
    except Exception:
        return None
```

#### Step 3: Update Configuration

Add exchange to `config/settings.py`:

```python
EXCHANGES = ["Binance", "OKX", "Bybit", "{Exchange}"]
```

#### Step 4: Update Main Script

Import and instantiate in `python/main.py`:

```python
from data_sources.{exchange}_exchange import {Exchange}Exchange

exchanges = {
    'binance': BinanceExchange(),
    'okx': OKXExchange(),
    'bybit': BybitExchange(),
    '{exchange}': {Exchange}Exchange(),
}
```

Update `fetch_valid_pairs`:

```python
binance_symbols, okx_symbols, bybit_symbols, {exchange}_symbols = await asyncio.gather(
    exchanges['binance'].fetch_symbols(client),
    exchanges['okx'].fetch_symbols(client),
    exchanges['bybit'].fetch_symbols(client),
    exchanges['{exchange}'].fetch_symbols(client),
)
```

Update `run_snapshot` and `run_live_stream` similarly.

#### Step 5: Cross-Exchange Bridges

**No changes needed!** The `cross_exchange.py` module automatically generates bridges for all exchanges listed in `EXCHANGES`.

### 4.2 Symbol Format Considerations

Different exchanges use different symbol formats:

| Exchange | Format | Example |
|----------|--------|---------|
| Binance  | No separator, uppercase | `BTCUSDT` |
| OKX      | Hyphen separator | `BTC-USDT` |
| Bybit    | No separator, uppercase | `BTCUSDT` |
| Kraken   | Varies, sometimes prefixed | `XXBTZUSD` |

**Solution**: Always implement normalization function like `to_{exchange}_format()` if needed.

---

## 5. API Reference Summary

### 5.1 Quick Reference Table

| Exchange | REST Base URL | WebSocket URL | Symbol Format | Price Field | Volume Field |
|----------|---------------|---------------|---------------|-------------|--------------|
| **Binance** | `https://api.binance.com` | `wss://stream.binance.com:9443` | `BTCUSDT` | `c` or `lastPrice` | `v` or `volume` |
| **OKX** | `https://www.okx.com` | `wss://ws.okx.com:8443/ws/v5/public` | `BTC-USDT` | `last` | `vol24h` |
| **Bybit** | `https://api.bybit.com` | `wss://stream.bybit.com/v5/public/spot` | `BTCUSDT` | `lastPrice` | `volume24h` |

### 5.2 WebSocket Subscription Formats

**Binance** (combined streams):

```plaintext
wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker
```

**OKX** (pub/sub model):

```json
{"op": "subscribe", "args": [{"channel": "tickers", "instId": "BTC-USDT"}]}
```

**Bybit** (topic-based, max 10 per request):

```json
{"op": "subscribe", "args": ["tickers.BTCUSDT", "tickers.ETHUSDT"]}
```

---

## Conclusion

This guide provides comprehensive technical details for all supported exchanges. When adding new exchanges, refer to the implementation steps and use existing exchanges as reference templates.

For architecture overview, see [architecture.md](architecture.md).
For general usage instructions, see [usage_guide.md](usage_guide.md).
