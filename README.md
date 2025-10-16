# Cryptocurrency Arbitrage Detection System

A high-performance real-time arbitrage detection system that monitors multiple cryptocurrency exchanges (Binance, OKX, and Bybit) and identifies profitable cross-exchange arbitrage opportunities using the Bellman-Ford algorithm.

## Overview

The system combines Python for data collection and C++ for high-performance graph analysis:

- **Python server**: Collects real-time market data via WebSocket connections
- **C++ detector**: Analyzes price graphs to identify negative cycles (arbitrage opportunities)
- **Communication**: TCP socket-based data streaming (localhost:5001)

## Project Structure

```plaintext
arbitrage_system/
├── config/                       # Configuration files
│   ├── settings.py               # Trading parameters (coins, thresholds)
│   └── network.py                # Network settings (host, port)
├── python/                       # Python data collection server
│   ├── core/
│   │   ├── cross_exchange.py     # Cross-exchange bridge logic
│   │   └── utils.py              # Utility functions
│   ├── data_sources/
│   │   ├── rest_api.py           # REST API clients
│   │   └── ws_stream.py          # WebSocket stream handlers
│   ├── communication/
│   │   └── socket_server.py      # TCP server for C++ communication
│   └── main.py                   # Entry point
├── cpp/                          # C++ arbitrage detector
│   ├── include/
│   │   ├── Graph.h               # Graph data structure
│   │   ├── SocketClient.hpp      # TCP client
│   │   └── json.hpp              # JSON parser (nlohmann)
│   ├── src/
│   │   ├── Graph.cpp             # Bellman-Ford implementation
│   │   ├── SocketClient.cpp      # Socket communication
│   │   └── main.cpp              # Entry point
│   └── build/
│       └── arbitrage_detector.exe
├── scripts/
│   └── compile.ps1               # Compilation script
├── output/                       # Runtime output
│   ├── snapshots/                # Initial market snapshots
│   ├── logs/                     # Execution logs
│   └── debug/                    # Debug information
└── docs/
    ├── architecture.md           # System architecture details
    └── usage_guide.md            # Extended usage guide
```

## How It Works

1. **Data Collection**: Python server connects to Binance, OKX, and Bybit WebSocket APIs to receive real-time order book updates
2. **Cross-Exchange Bridges**: System generates virtual edges between identical assets on different exchanges (e.g., BTC_Binance ↔ BTC_OKX) with price 1.0 to represent transfer possibilities
3. **Graph Construction**: Market data is structured as a weighted directed graph where:
   - Nodes = assets on each exchange (e.g., BTC_Binance, ETH_OKX)
   - Edges = conversion rates (negative log of price for Bellman-Ford)
   - Cross-exchange edges = virtual bridges for asset transfers between platforms
4. **Arbitrage Detection**: C++ detector offers three detection modes (see [Detection Modes](#detection-modes)):
   - **Classic Mode**: Multi-source Bellman-Ford from all nodes
   - **Super-Source Mode**: Hybrid algorithm with super-source + per-exchange nodes
   - **Benchmark Mode**: Performance comparison between both algorithms
5. **Real-time Updates**: Continuous data streaming ensures detection of opportunities as they emerge

**Note on Cross-Exchange Arbitrage**: While the system models cross-exchange transfers as instant 1:1 bridges, real-world execution involves:

- Transfer time (blockchain confirmations: minutes to hours)
- Network fees (variable based on blockchain congestion)
- Exchange deposit/withdrawal fees
- Price slippage during transfer window
- Non-atomic execution risk

For production use, these costs should be incorporated into the edge weights. The current implementation is suitable for research and identifying theoretical opportunities.

## Detection Modes

When you launch the C++ detector, you'll be prompted to select one of three detection modes:

```plaintext
=== Arbitrage Detection System ===
1. All sources
2. Single source
3. Benchmark (performance comparison)
Choice:
```

### Mode 1: Classic (All Sources)

**Algorithm**: Multi-source Bellman-Ford

- Runs Bellman-Ford from **every node** in the graph
- Comprehensive detection: finds all possible arbitrage cycles
- **Complexity**: O(V × E) per node, O(V² × E) total for V nodes
- **Best for**: Complete arbitrage discovery, research

**Example**: With 67 nodes (22 coins × 3 exchanges + bridges), runs Bellman-Ford 67 times per iteration.

### Mode 2: Super-Source (Single Source)

**Algorithm**: Hybrid Super-Source Bellman-Ford

- Creates virtual **SUPER_SOURCE** node connected to all graph nodes
- Runs Bellman-Ford from super-source + one node per exchange (4 total runs)
- **Complexity**: O(V × E) × 4 runs = significantly faster than classic
- **Best for**: Production use, real-time detection with performance constraints

**How it works**:

1. Add SUPER_SOURCE node with weight-0 edges to all nodes
2. Run Bellman-Ford from SUPER_SOURCE (detects cross-exchange cycles)
3. Run Bellman-Ford from one node per exchange (detects intra-exchange cycles)
4. Result: 4 Bellman-Ford runs vs. 67 in classic mode

**Example**: Same 67-node graph requires only 4 Bellman-Ford runs (1 super-source + 3 exchanges).

### Mode 3: Benchmark (Performance Comparison)

**Purpose**: Compare performance between Classic and Super-Source algorithms

- Runs both algorithms simultaneously on same data
- 10-second warmup period for graph initialization
- Reports every 5 seconds with detailed metrics
- Separate cycle caches to ensure fair comparison

**Output example**:

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

**Best for**: Performance analysis, algorithm comparison, research papers

## Requirements

### Python

- Python 3.10 or higher
- Dependencies (install via `pip install -r requirements.txt`):

  ```txt
  websockets
  httpx
  aiohttp
  asyncio (built-in)
  ```

### C++

- **MinGW-w64** with g++ compiler (C++17 support required)
- nlohmann/json library (included in `cpp/include/`)
- Windows Sockets 2 library (ws2_32)

### System

- Windows 10/11 (for PowerShell scripts) or Linux/macOS with modifications
- Minimum 256 MB RAM
- Network connection for exchange APIs

## Quick Start

### Prerequisites

1. **Install Python dependencies** (first time only):

   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Compile C++ detector** (first time only):

   ```powershell
   .\scripts\compile.ps1
   ```

### Automatic Startup (Recommended)

The easiest way to start the system is using the automated startup script:

```powershell
.\scripts\start.ps1
```

This script will:

- ✅ Verify all prerequisites (venv, compiled C++ executable)
- ✅ Check port 5001 availability (with option to kill conflicting processes)
- ✅ Start Python server in a separate window
- ✅ Wait for server initialization
- ✅ Start C++ detector in a separate window
- ✅ Provide status updates and monitoring instructions

**Output**: Two PowerShell windows will open:

1. **Python Server** - Shows WebSocket connections and data streaming
2. **C++ Detector** - Shows real-time arbitrage detection

To stop the system, press `CTRL+C` in both windows or simply close them.

### Manual Startup (Advanced)

If you prefer to start components individually:

**1. Start Python Server** (in terminal 1):

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run Python server
python python/main.py
```

The server will:

- Connect to Binance, OKX, and Bybit WebSocket streams
- Start TCP server on localhost:5001
- Save initial snapshots to `output/snapshots/`

**2. Launch C++ Detector** (in terminal 2):

```bash
.\cpp\build\arbitrage_detector.exe
```

The detector will:

- Prompt you to select a detection mode (1: Classic, 2: Super-Source, 3: Benchmark)
- Connect to Python server on localhost:5001
- Begin processing market data
- Output detected arbitrage opportunities to console

**Mode selection**: Enter `1`, `2`, or `3` when prompted. See [Detection Modes](#detection-modes) for detailed comparison.

**Note**: Start the Python server first, then the C++ detector. The C++ detector needs the Python server to be listening on port 5001.

## Configuration

### Trading Parameters (`config/settings.py`)

```python
# Assets to monitor
COINS = ["BTC", "ETH", "USDT", "BNB", "SOL"]

# Minimum profit threshold (0.005 = 0.5%)
PROFIT_THRESHOLD = 0.005

# Minimum cycle length for valid arbitrage
MIN_CYCLE_LENGTH = 3

# Maximum cycle length to report
MAX_CYCLE_LENGTH = 6
```

### Network Settings (`config/network.py`)

```python
# TCP server configuration
HOST = "127.0.0.1"
PORT = 5001

# Buffer sizes
BUFFER_SIZE = 8192
```

### Exchange Configuration

Modify `python/data_sources/ws_stream.py` to add/remove trading pairs or exchanges.

## Output

### Snapshots

Initial market state saved to `output/snapshots/`:

- `Initial_Snapshot_Binance.csv`
- `Initial_Snapshot_OKX.csv`
- `Initial_Snapshot_Bybit.csv`

### Logs

Runtime logs in `output/logs/`:

- Connection status
- Update frequencies
- Detected arbitrage opportunities

### Console Output

Real-time arbitrage detection:

```plaintext
[2025-10-08 23:30:03] [!] Arbitrage found!
Profit = 1.0073x (0.73%)
Path: USDT_Binance -> BTC_Binance -> BTC_OKX -> USDT_OKX -> USDT_Binance

=== Arbitrages found @ 23:30:03 => 1 ===
```

## Troubleshooting

### Port Already in Use

```plaintext
Error: [Errno 10048] Only one usage of each socket address
```

**Solution**: Kill process using port 5001 or change `PORT` in `config/network.py`

```powershell
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

### No Arbitrage Detected

**Possible causes**:

- Profit threshold too high → Lower `PROFIT_THRESHOLD` in settings
- Insufficient liquidity → Market spreads are tight
- Network latency → Opportunities vanish before detection

### WebSocket Connection Failures

**Solution**: Check internet connection and exchange API status:

- Binance: <https://binance.com/en/support/announcement>
- OKX: <https://www.okx.com/support/hc/en-us>
- Bybit: <https://www.bybit.com/en/announcement-info>

### C++ Compilation Errors

**Solution**: Ensure MinGW-w64 with g++ is installed and in PATH

```bash
# Verify g++ is available
g++ --version  # Should support C++17 (gcc 7.0+)
```

**Windows installation**: Download MinGW-w64 from [winlibs.com](https://winlibs.com) or use MSYS2

## Documentation

- [architecture.md](docs/architecture.md) - Detailed system architecture
- [usage_guide.md](docs/usage_guide.md) - Extended usage examples

## License

This project is intended for educational and research purposes.

## Disclaimer

**This software is for research and educational purposes only.** Cryptocurrency trading involves substantial risk. The authors are not responsible for any financial losses incurred through the use of this software. Always conduct thorough testing and risk assessment before deploying any trading system.
