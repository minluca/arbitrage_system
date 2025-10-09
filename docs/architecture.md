# Arbitrage Detection System - Architecture

## 1. Overview

Distributed system for real-time detection of cross-exchange arbitrage opportunities in cryptocurrency markets. The architecture is divided into two main components:

- **Python**: Data collection from multiple exchanges (Binance, OKX) via REST API and WebSocket
- **C++**: Arbitrage detection using Bellman-Ford algorithm on weighted graph

The two components communicate via TCP socket on `localhost:5001`.

## 2. Python Components

### 2.1 Main Orchestrator ([python/main.py](../python/main.py))

System entry point. Coordinates the following phases:

1. **Initialization** (`fetch_valid_pairs`):
   - Fetch valid symbols from Binance and OKX
   - Filter symbols based on `SYMBOLS` (pairs generated from `COINS`)

2. **Initial Snapshot** (`run_snapshot`):
   - Parallel REST requests with `asyncio.gather`
   - CSV output: `Initial_Snapshot_Binance.csv`, `Initial_Snapshot_OKX.csv`

3. **Live Streaming** (`run_live_stream`):
   - Create shared asyncio queue
   - Launch parallel tasks: `stream_binance_ws`, `stream_okx_ws`, `socket_consumer`
   - Graceful shutdown handling (CTRL+C)

### 2.2 REST API ([python/data_sources/rest_api.py](../python/data_sources/rest_api.py))

Fetch initial snapshots via REST API:

- **Binance**:
  - Symbols: `GET /api/v3/exchangeInfo` (filter `status=TRADING`)
  - Prices: `GET /api/v3/ticker/24hr` (lastPrice, volume)

- **OKX**:
  - Symbols: `GET /api/v5/public/instruments?instType=SPOT` (filter `state=live`)
  - Prices: `GET /api/v5/market/tickers?instType=SPOT` (last, vol24h)

Fallback to default symbols (`BTCUSDT`, `ETHUSDT`) on error.

### 2.3 WebSocket Streaming ([python/data_sources/ws_stream.py](../python/data_sources/ws_stream.py))

Real-time ticker streaming via WebSocket:

- **Generic Function** (`stream_ws`):
  - WebSocket connection with keepalive (ping_interval=20s)
  - Exponential retry (backoff: 1s → 30s max)
  - Custom parsing per exchange
  - Push data to `asyncio.Queue`

- **Binance** (`stream_binance_ws`):
  - URL: `wss://stream.binance.com:9443/stream?streams={streams}`
  - Stream format: `btcusdt@ticker/ethusdt@ticker/...`
  - Parser: `parse_binance` (field `c` = close price, `v` = volume)

- **OKX** (`stream_okx_ws`):
  - URL: `wss://ws.okx.com:8443/ws/v5/public`
  - Requires subscription: `{"op":"subscribe","args":[{"channel":"tickers","instId":"BTC-USDT"}]}`
  - Parser: `parse_okx` (fields `last`, `vol24h`)

### 2.4 Cross-Exchange Bridges ([python/core/cross_exchange.py](../python/core/cross_exchange.py))

Generate virtual edges to connect same asset across exchanges:

- **Function** `build_cross_exchange_bridges(asset)`:
  - Create **bidirectional** 1:1 bridges between every exchange pair
  - Example: `BTC_Binance → BTC_OKX` (price=1.0, exchange="Cross")
  - Assumption: zero transfer cost (no fees)

- **Function** `get_all_cross_exchange_bridges(assets)`:
  - Generate all bridges for `COINS` list
  - Called once at startup (not per update)

### 2.5 Socket Server ([python/communication/socket_server.py](../python/communication/socket_server.py))

TCP server forwarding data to C++ client:

- **Protocol**:
  1. Header: 16 bytes with message length (zero-padded)
  2. Payload: JSON serialized

- **Flow**:
  1. Bind on `127.0.0.1:5001` and wait for connection
  2. Send initial cross-exchange bridges (`send_initial_bridges`)
  3. Loop: fetch from queue → serialize → send
  4. Debug log every 500 messages

### 2.6 Utilities ([python/core/utils.py](../python/core/utils.py))

Constants and helper functions:

- **Constants**:
  - `COINS`: 22 assets (BTC, ETH, stablecoins, etc.)
  - `SYMBOLS`: 462 pairs generated (cartesian product, excluding base==quote)
  - `CSV_FIELDS`: `["timestamp", "symbol", "base", "quote", "price", "volume", "exchange"]`

- **Functions**:
  - `now_ts()`: timestamp with milliseconds (`%Y-%m-%d %H:%M:%S.%f`)
  - `norm_symbol()`: symbol normalization (`BTC-USDT` → `BTCUSDT`)
  - `split_symbol()`: split base/quote using `COINS`
  - `parse_binance/okx()`: exchange-specific WebSocket parsers

## 3. C++ Components

### 3.1 Main Entry Point ([cpp/src/main.cpp](../cpp/src/main.cpp))

Main loop for receiving and processing:

```cpp
Socket::Client client("127.0.0.1", 5001);
Graph g;

while (true) {
    std::string msg = client.receiveMessage();
    g.processMessage(msg);  // JSON parsing + graph update
    g.findArbitrage();      // Bellman-Ford
}
```

### 3.2 Graph Structure ([cpp/include/Graph.h](../cpp/include/Graph.h), [cpp/src/Graph.cpp](../cpp/src/Graph.cpp))

#### Data Structures

```cpp
struct Edge {
    int source, destination;
    double weight;          // -log(price)
    double price;           // actual price
    std::string exchange;   // "Binance" / "OKX" / "Cross"
    std::string symbol;
};

class Graph {
    std::unordered_map<std::string, int> nodeIds;  // name → ID
    std::vector<std::string> nodeNames;            // ID → name
    std::vector<Edge> edges;
    // ...cycle deduplication...
};
```

#### Main Functions

- **`addNode(name)`**: Add node (or return existing ID)

- **`addOrUpdateEdge(source, dest, price, exchange, symbol)`**:
  - **Price Validation**:
    - Reject if `p <= 0` or `!isfinite(p)`
    - Reject if `p < 1e-8` or `p > 1e8` (garbage data)
    - Warn if stablecoin pair with `p < 0.99` or `p > 1.01`
    - Reject cross bridges if `price != 1.0`
  - **Conversion**: `weight = -log(price)`
  - **Reverse Edge**: Auto-generate for non-cross edges (`weight_inv = -log(1/price)`)
  - **Update**: Overwrite if edge already exists

- **`processMessage(json_msg)`**:
  - Parse JSON: extract `base`, `quote`, `price`, `exchange`
  - Exchange suffix: `BTC` → `BTC_Binance` (if not already present)
  - Call `addOrUpdateEdge`

- **`findArbitrage()`**: See section 6

### 3.3 Socket Client ([cpp/include/SocketClient.hpp](../cpp/include/SocketClient.hpp))

TCP client for Python communication:

- **Constructor**: `Client(ip, port)` → Winsock2 connection
- **`receiveMessage()`**:
  1. Read 16-byte header (message length)
  2. Read JSON payload
  3. Return string

## 4. End-to-End Data Flow

```plaintext
┌───────────────────────────────────────────────────────────┐
│                        PYTHON LAYER                       │
│                                                           │
│            ┌──────────────┐  ┌──────────────┐             │       
│            │   Binance    │  │     OKX      │             │       
│            │  WebSocket   │  │  WebSocket   │             │       
│            └──────┬───────┘  └───────┬──────┘             │       
│                   │                  │                    │       
│                   └─────────┬────────┘                    │       
│                             ▼                             │       
│                   ┌──────────────────┐                    │       
│                   │  parse_binance   │                    │       
│                   │    parse_okx     │                    │       
│                   └─────────┬────────┘                    │       
│                             ▼                             │       
│                   ┌──────────────────┐                    │       
│                   │  asyncio.Queue   │                    │       
│                   └─────────┬────────┘                    │       
│                             ▼                             │       
│                   ┌──────────────────┐                    │       
│                   │ socket_consumer  │                    │       
│                   │   (TCP Server)   │                    │       
│                   └─────────┬────────┘                    │       
│                             │ localhost:5001              │       
└─────────────────────────────┼─────────────────────────────┘
                              │ TCP Socket
                              ▼
┌───────────────────────────────────────────────────────────┐
│                         C++ LAYER                         │
│                                                           │
│                   ┌──────────────────┐                    │
│                   │  SocketClient    │                    │
│                   │ receiveMessage() │                    │
│                   └─────────┬────────┘                    │
│                             ▼                             │
│                   ┌──────────────────┐                    │
│                   │ Graph::process   │                    │
│                   │    Message()     │                    │
│                   └─────────┬────────┘                    │
│                             ▼                             │
│                   ┌──────────────────┐                    │
│                   │ addOrUpdateEdge  │                    │
│                   │  (update graph)  │                    │
│                   └─────────┬────────┘                    │
│                             ▼                             │
│                   ┌──────────────────┐                    │
│                   │  findArbitrage() │                    │
│                   │  (Bellman-Ford)  │                    │
│                   └─────────┬────────┘                    │
│                             ▼                             │
│                      Console Output                       │
│                      [!] Arbitrage found!                 │
│                      Profit = 1.0012x                     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## 5. Graph Representation

### 5.1 Nodes

Each asset on an exchange becomes a node:

- Format: `{ASSET}_{EXCHANGE}`
- Examples: `BTC_Binance`, `ETH_OKX`, `USDT_Binance`

### 5.2 Market Edges

Represent available trading pairs:

- **Weight**: `weight = -log(price)`
  - Negative cycle ⟺ Σ(-log(price)) < 0 ⟺ Π(price) > 1 ⟺ Arbitrage!

- **Direct Edge**: `BTC_Binance → USDT_Binance` (BTCUSDT pair)
  - `price = 50000`, `weight = -log(50000) ≈ -10.82`

- **Reverse Edge** (auto-generated):
  - `USDT_Binance → BTC_Binance`
  - `price = 1/50000 = 0.00002`, `weight = -log(0.00002) ≈ 10.82`

### 5.3 Cross-Exchange Bridges

Virtual edges for inter-exchange transfers:

- **Properties**:
  - `price = 1.0` (1:1 transfer, zero fees assumption)
  - `weight = -log(1.0) = 0`
  - `exchange = "Cross"`

- **Example**:
  - `BTC_Binance → BTC_OKX` (bridge)
  - `BTC_OKX → BTC_Binance` (reverse bridge)

### 5.4 Arbitrage Cycle Example

```plaintext
BTC_Binance → USDT_Binance  (sell BTC, price 50000)
   ↓
USDT_Binance → USDT_OKX     (transfer, price 1.0)
   ↓
USDT_OKX → BTC_OKX          (buy BTC, price 0.00002001)
   ↓
BTC_OKX → BTC_Binance       (transfer, price 1.0)
```

**Profit**: 50000 × 1.0 × 0.00002001 × 1.0 = 1.0005 (0.05% gain)

## 6. Bellman-Ford Algorithm

### 6.1 Implementation ([Graph.cpp:236-403](../cpp/src/Graph.cpp))

```cpp
void Graph::findArbitrage() {
    // Warm-up: ignore first 3 seconds (data stabilization)

    // Bellman-Ford from each START node
    for (int start = 0; start < V; ++start) {
        std::vector<double> dist(V, ∞);
        std::vector<int> parent(V, -1);
        dist[start] = 0.0;

        // PHASE 1: Relaxation (V-1 iterations)
        for (int i = 0; i < V-1; ++i) {
            for (auto& e : edges) {
                if (dist[e.source] + e.weight < dist[e.destination]) {
                    dist[e.destination] = dist[e.source] + e.weight;
                    parent[e.destination] = e.source;
                }
            }
        }

        // PHASE 2: Negative cycle detection (V-th iteration)
        for (auto& e : edges) {
            if (dist[e.source] + e.weight < dist[e.destination] - EPS) {
                // Negative cycle found!

                // Reconstruct cycle from parents
                std::vector<int> cycle = reconstruct_cycle(parent, e.destination);

                // Calculate real profit: Π(price)
                double profit = 1.0;
                for (edge in cycle) profit *= edge.price;

                // Filter invalid
                if (profit <= 1.000001 || profit > 10.0) continue;
                if (cycle.size() < 3) continue;

                // Deduplication
                if (isDuplicateCycle(canonicalSignature(cycle, profit)))
                    continue;

                // PRINT ARBITRAGE
                std::cout << "[!] Arbitrage found! "
                          << "Profit = " << profit << "x | "
                          << "Path: " << path << "\n";
            }
        }
    }
}
```

### 6.2 Complexity

- **Time**: O(V² · E)
  - V outer iterations (each start node)
  - V-1 + 1 inner iterations
  - E edges per iteration

- **Space**: O(V + E)
  - dist, parent vectors: O(V)
  - Edge list: O(E)

### 6.3 Optimizations

1. **Cycle Deduplication**:
   - `canonicalizeCycle()`: Normalize cycle (rotation + lexicographic reverse)
   - `canonicalSignature()`: Unique string `{profit}|{node1}->{node2}->...`
   - LRU cache: `recentSet` (hash set) + `recentCycles` (deque, max 100)

2. **Price Validation**:
   - Reject garbage data (`p < 1e-8` or `p > 1e8`)
   - Warn anomalous stablecoin pairs (`p < 0.99` or `p > 1.01`)
   - Filter unrealistic profits (`profit > 10.0`)

3. **Warm-up**:
   - Ignore first 3 seconds for stream stabilization

4. **Aggregated Logging**:
   - Print only when second changes
   - Count arbitrages per second (not per message)

## 7. Technologies and Dependencies

### 7.1 Python

- **asyncio**: Asynchronous concurrency (WebSocket + Queue)
- **websockets**: WebSocket client for Binance/OKX
- **httpx**: Async HTTP client (REST API)
- **pandas**: CSV snapshot manipulation
- **json**: TCP message serialization

### 7.2 C++

- **STL**: `<vector>`, `<unordered_map>`, `<deque>`, `<algorithm>`
- **nlohmann/json**: JSON parsing (header-only)
- **Winsock2**: TCP socket (Windows)
- **chrono/iomanip**: Timestamp and output formatting

### 7.3 Configuration

**[config/settings.py](../config/settings.py)**:

- `COINS`: 22 assets
- `EXCHANGES`: ["Binance", "OKX"]
- `PROFIT_THRESHOLD`: 1.00005 (0.005%)
- `MIN_CYCLE_LENGTH`: 3

**[config/network.py](../config/network.py)**:

- `HOST`: "127.0.0.1"
- `PORT`: 5001
- `WS_PING_INTERVAL`: 20s
- `WS_RECONNECT_DELAY`: 1s → 30s (exponential backoff)

## 8. Execution

1. **Start Python** (server):

   ```bash
   python .\python\main.py
   ```

2. **Start C++** (client):

   ```bash
   .\cpp\build\arbitrage_detector.exe
   ```

3. **Expected Output**:

   ```plaintext
   [Python Server] Waiting for connection on 127.0.0.1:5001...
   [Python Server] Connected from ('127.0.0.1', 52341)
   [Python Server] Sent 88 cross-exchange bridges
   [Binance] Connected. Stream active...
   [OKX] Connected. Stream active...

   [2025-01-15 14:23:45] [!] Arbitrage found!
   Profit = 1.0012345678x |
   Path: BTC_Binance -> USDT_Binance -> USDT_OKX -> BTC_OKX -> BTC_Binance
   ```

## 9. Limitations and Assumptions

1. **Zero Fees**: Cross-exchange bridges assume zero cost (unrealistic)
2. **Latency**: Network delay Python <-> C++ and exchange <-> client not modeled
3. **Slippage**: Does not account for price variation during order execution
4. **Liquidity**: Does not verify sufficient volume for real profitability
