# Arbitrage Detection System - Architecture

## 1. Overview

Distributed system for real-time detection of cross-exchange arbitrage opportunities in cryptocurrency markets. The architecture is divided into two main components:

- **Python**: Data collection from multiple exchanges (Binance, OKX, Bybit) via REST API and WebSocket
- **C++**: Arbitrage detection using Bellman-Ford algorithm on weighted graph

The two components communicate via TCP socket on `localhost:5001`.

## 2. Python Components

### 2.1 Main Orchestrator ([python/main.py](../python/main.py))

System entry point. Coordinates the following phases:

1. **Initialization** (`fetch_valid_pairs`):
   - Fetch valid symbols from Binance, OKX, and Bybit
   - Filter symbols based on `SYMBOLS` (pairs generated from `COINS`)

2. **Initial Snapshot** (`run_snapshot`):
   - Parallel REST requests with `asyncio.gather`
   - CSV output: `Initial_Snapshot_Binance.csv`, `Initial_Snapshot_OKX.csv`, `Initial_Snapshot_Bybit.csv`

3. **Live Streaming** (`run_live_stream`):
   - Create shared asyncio queue
   - Launch parallel tasks: `stream_binance_ws`, `stream_okx_ws`, `stream_bybit_ws`, `socket_consumer`
   - Graceful shutdown handling (CTRL+C)

### 2.2 Exchange Classes

Each exchange has a dedicated class implementing `ExchangeBase`:

- **Binance** ([python/data_sources/binance_exchange.py](../python/data_sources/binance_exchange.py)):
  - Symbols: `GET /api/v3/exchangeInfo` (filter `status=TRADING`)
  - Prices: `GET /api/v3/ticker/24hr` (lastPrice, volume)
  - WebSocket: `wss://stream.binance.com:9443/stream?streams={symbols}@ticker`

- **OKX** ([python/data_sources/okx_exchange.py](../python/data_sources/okx_exchange.py)):
  - Symbols: `GET /api/v5/public/instruments?instType=SPOT` (filter `state=live`)
  - Prices: `GET /api/v5/market/tickers?instType=SPOT` (last, vol24h)
  - WebSocket: `wss://ws.okx.com:8443/ws/v5/public`

- **Bybit** ([python/data_sources/bybit_exchange.py](../python/data_sources/bybit_exchange.py)):
  - Symbols: `GET /v5/market/instruments-info?category=spot` (filter `status=Trading`)
  - Prices: `GET /v5/market/tickers?category=spot` (lastPrice, volume24h)
  - WebSocket: `wss://stream.bybit.com/v5/public/spot` (max 10 tickers per subscription)

Fallback to default symbols (`BTCUSDT`, `ETHUSDT`) on error.

### 2.3 WebSocket Streaming

Real-time ticker streaming via WebSocket (each exchange implements `stream_ws`):

- **Common Features**:
  - WebSocket connection with keepalive (ping_interval=20s)
  - Exponential retry (backoff: 1s → 30s max)
  - Custom parsing per exchange via parsers
  - Push data to `asyncio.Queue`

- **Binance**:
  - URL: `wss://stream.binance.com:9443/stream?streams={streams}`
  - Stream format: `btcusdt@ticker/ethusdt@ticker/...`
  - Parser: `parse_binance` (field `c` = close price, `v` = volume)

- **OKX**:
  - URL: `wss://ws.okx.com:8443/ws/v5/public`
  - Subscription: `{"op":"subscribe","args":[{"channel":"tickers","instId":"BTC-USDT"}]}`
  - Parser: `parse_okx` (fields `last`, `vol24h`)

- **Bybit**:
  - URL: `wss://stream.bybit.com/v5/public/spot`
  - Subscription: `{"op":"subscribe","args":["tickers.BTCUSDT", ...]}` (batched in groups of 10)
  - Parser: `parse_bybit` (fields `lastPrice`, `volume24h`)

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

User selects detection mode at startup, then enters main loop:

```cpp
// Mode selection
std::cout << "=== Arbitrage Detection System ===\n";
std::cout << "1. All sources\n";
std::cout << "2. Single source\n";
std::cout << "3. Benchmark (performance comparison)\n";
int mode;
std::cin >> mode;

Socket::Client client("127.0.0.1", 5001);
Graph g;

while (true) {
    std::string msg = client.receiveMessage();
    g.processMessage(msg);  // JSON parsing + graph update

    if (mode == 1)
        g.findArbitrage();              // Classic: Multi-source BF
    else if (mode == 2)
        g.findArbitrageSuperSource();   // Super-source: Hybrid BF
    else
        g.runBenchmark();               // Benchmark: Both algorithms
}
```

**Mode Details**:
- **Mode 1 (Classic)**: Runs Bellman-Ford from every node - comprehensive but O(V² × E)
- **Mode 2 (Super-source)**: Hybrid algorithm with 4 BF runs - **16-17x faster**
- **Mode 3 (Benchmark)**: Runs both algorithms simultaneously for performance comparison

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

- **`findArbitrage()`**: Classic multi-source Bellman-Ford (see section 6.1)
- **`findArbitrageSuperSource()`**: Super-source hybrid algorithm (see section 6.2)
- **`runBenchmark()`**: Performance comparison mode (see section 6.3)
- **`ensureSuperSourceEdges()`**: Creates/updates super-source node connections
- **`warmupActive()`**: Checks if system is in warmup period (3 seconds)

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

## 6. Arbitrage Detection Algorithms

The system implements three detection modes with different performance characteristics.

### 6.1 Classic Mode - Multi-Source Bellman-Ford

**Implementation**: `Graph::findArbitrage()` ([Graph.cpp:220-372](../cpp/src/Graph.cpp))

**Algorithm**:
```cpp
void Graph::findArbitrage() {
    // 3-second warm-up for data stabilization
    if (warmup_active) return;

    // Run Bellman-Ford from EVERY node
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

        // PHASE 2: Negative cycle detection
        for (auto& e : edges) {
            if (dist[e.source] + e.weight < dist[e.destination] - EPS) {
                // Cycle found! Reconstruct and validate...
                std::vector<int> cycle = reconstruct(parent, e.destination);
                double profit = calculate_profit(cycle);

                if (profit > 1.000001 && !isDuplicate(cycle))
                    print_arbitrage(cycle, profit);
            }
        }
    }
}
```

**Characteristics**:
- **Completeness**: Detects ALL possible arbitrage cycles
- **Complexity**: O(V² × E) - runs V times, each O(V × E)
- **Use case**: Research, complete market analysis

**Example**: With 67 nodes and 4891 edges:
- 67 Bellman-Ford runs per iteration
- ~408 million edge relaxations per iteration
- ~10ms per iteration

### 6.2 Super-Source Mode - Hybrid Algorithm

**Implementation**: `Graph::findArbitrageSuperSource()` ([Graph.cpp:423-555](../cpp/src/Graph.cpp))

**Key Innovation**: Instead of running BF from all nodes, creates a virtual super-source and runs BF only 4 times:

**Algorithm**:
```cpp
void Graph::findArbitrageSuperSource() {
    // Ensure SUPER_SOURCE node exists with edges to all nodes
    ensureSuperSourceEdges();  // Adds edges: SUPER_SOURCE -> all nodes (weight=0)

    auto runBellmanFord = [&](int startNode) {
        // Standard BF from startNode...
        // (same relaxation + cycle detection as classic)
    };

    // 1. Run from super-source (detects cross-exchange cycles)
    runBellmanFord(superSourceId);

    // 2. Run once per exchange (detects intra-exchange cycles)
    std::set<std::string> processedExchanges;
    for (int node = 0; node < V; ++node) {
        std::string exchange = extractExchange(nodeNames[node]);
        if (!exchange.empty() && !processedExchanges.count(exchange)) {
            processedExchanges.insert(exchange);
            runBellmanFord(node);  // One BF per exchange
        }
    }
    // Total: 4 BF runs (1 super + 3 exchanges: Binance, OKX, Bybit)
}
```

**How Super-Source Works**:
1. Add virtual node `SUPER_SOURCE`
2. Connect to ALL graph nodes with weight=0 edges
3. Running BF from super-source reaches all nodes in one hop
4. Detects cycles reachable from anywhere in the graph

**Why Add Per-Exchange Runs?**:
- Super-source detects **cross-exchange** cycles efficiently
- Per-exchange runs catch **intra-exchange** cycles (e.g., BTC→ETH→USDT→BTC all on Binance)
- Total: 4 runs vs. 67 in classic mode

**Characteristics**:
- **Efficiency**: **16-17x faster** than classic mode
- **Complexity**: O(4 × V × E) = O(V × E) effectively
- **Coverage**: Detects both cross-exchange and intra-exchange arbitrage
- **Use case**: Production, real-time detection

**Example**: Same 67-node graph:
- 4 Bellman-Ford runs per iteration
- ~24 million edge relaxations per iteration
- <1ms per iteration

### 6.3 Benchmark Mode - Performance Comparison

**Implementation**: `Graph::runBenchmark()` ([Graph.cpp:782-904](../cpp/src/Graph.cpp))

**Purpose**: Run both algorithms simultaneously to compare performance.

**Algorithm**:
```cpp
void Graph::runBenchmark() {
    // 10-second warmup for graph stabilization
    if (!warmupDone) {
        if (elapsed < 10) return;
        warmupDone = true;
    }

    // Separate cycle caches for fair comparison
    recentCycles = cacheClassic;
    recentSet = setClassic;
    findArbitrageQuiet(statsClassic);  // No console output
    cacheClassic = recentCycles;

    recentCycles = cacheSuper;
    recentSet = setSuper;
    findArbitrageSuperSourceQuiet(statsSuper);  // No console output
    cacheSuper = recentCycles;

    iterations++;

    // Print report every 5 seconds
    if (elapsed >= 5) {
        print_benchmark_report(statsClassic, statsSuper, iterations);
        reset_stats();
    }
}
```

**Output Example**:
```plaintext
========== BENCHMARK REPORT (2025-10-16 21:15:30) ==========
Iterations: 1247
Graph size: 67 nodes, 4891 edges

[Classic Mode - Multi-Source Bellman-Ford]
  Cycles found:       43
  Bellman-Ford runs:  83629
  Edges processed:    408,954,839
  Total time:         12.456s
  Avg time/iteration: 0.010s

[Super-Source Hybrid Mode - 4x Bellman-Ford]
  Cycles found:       42
  Bellman-Ford runs:  4988
  Edges processed:    24,389,068
  Total time:         0.742s
  Avg time/iteration: 0.001s

Performance:
  Speedup: 16.79x faster
  Time savings: 1579.0%
  BF reduction: 16.8x fewer runs
=======================================================
```

**Key Features**:
- Separate cycle caches ensure no cross-contamination
- Silent execution (`findArbitrageQuiet`) for accurate timing
- Detailed metrics: cycles found, BF runs, edges processed, time

### 6.4 Shared Optimizations (All Modes)

1. **Cycle Deduplication**:
   - `canonicalizeCycle()`: Normalize cycle (rotation + lexicographic ordering)
   - `canonicalSignature()`: Unique string identifier
   - LRU cache: 100 most recent cycles

2. **Price Validation**:
   - Reject if `price <= 0` or `!isfinite(price)`
   - Reject extreme values (`price < 1e-8` or `price > 1e8`)
   - Warn stablecoin anomalies (`price < 0.99` or `price > 1.01` for USDT/USDC pairs)
   - Reject cross-exchange bridges with `price != 1.0`

3. **Profit Filtering**:
   - Minimum: `profit > 1.000001` (0.0001%)
   - Maximum: `profit < 10.0` (exclude data errors)
   - Minimum cycle length: 3 edges

4. **Warm-up Period**:
   - Modes 1 & 2: 3 seconds
   - Mode 3 (Benchmark): 10 seconds
   - Prevents false positives during graph initialization

5. **Aggregated Logging**:
   - Print summary per second (not per message)
   - Count arbitrages: "=== Arbitrages found @ HH:MM:SS => N ==="

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
- `EXCHANGES`: ["Binance", "OKX", "Bybit"]
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
