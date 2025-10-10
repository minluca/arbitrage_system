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
2. **Cross-Exchange Bridges**: System generates virtual edges between identical assets on different exchanges (e.g., BTC_Binance � BTC_OKX)
3. **Graph Construction**: Market data is structured as a weighted directed graph where:
   - Nodes = trading pairs on each exchange
   - Edges = conversion rates (negative log of price for Bellman-Ford)
   - Cross-exchange edges = deposit/withdrawal paths
4. **Arbitrage Detection**: C++ detector runs Bellman-Ford algorithm to identify negative cycles (profitable arbitrage loops)
5. **Real-time Updates**: Continuous data streaming ensures detection of opportunities as they emerge

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

- C++17 compatible compiler (MSVC, GCC, or Clang)
- CMake 3.10+ (optional, for build)
- nlohmann/json library (included in `cpp/include/`)

### System

- Windows 10/11 (for PowerShell scripts) or Linux/macOS with modifications
- Minimum 256 MB RAM
- Network connection for exchange APIs

## Quick Start

### 1. Compile C++ Detector

```powershell
.\scripts\compile.ps1
```

Or manually:

**Windows:**

```bash
cd cpp
g++ -std=c++17 -O3 -o build/arbitrage_detector.exe src/main.cpp src/Graph.cpp src/SocketClient.cpp -Iinclude -lws2_32
```

**Linux/Mac:**

```bash
cd cpp
g++ -std=c++17 -O3 -o build/arbitrage_detector src/*.cpp -Iinclude -lpthread
```

### 2. Start Python Server

```bash
python python/main.py
```

Or if already in project root:

```bash
cd arbitrage_system
python python/main.py
```

The server will:

- Connect to Binance, OKX, and Bybit WebSocket streams
- Start TCP server on localhost:5001
- Log initial snapshots to `output/snapshots/`

### 3. Launch C++ Detector

```bash
.\cpp\build\arbitrage_detector.exe
```

The detector will:

- Connect to Python server
- Begin processing market data
- Output detected arbitrage opportunities to console and logs

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
[2025-10-08 23:30:03] [!] Arbitraggio trovato! 
Profit = 1.0073x (0.73%)
Percorso: USDT_Binance -> BTC_Binance -> BTC_OKX -> USDT_OKX -> USDT_Binance

=== Arbitraggi trovati @ 23:30:03 => 1 ===
```

## Performance

- **Memory Usage**: ~150 MB (Python + C++ combined)
- **Throughput**: ~100-200 messages/second
- **Latency**: <10ms for cycle detection
- **Scalability**: Handles 50+ trading pairs simultaneously

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

**Solution**: Ensure C++17 support and include paths are correct

```bash
# Verify compiler version
g++ --version  # Should be 7.0+
cl /?          # MSVC 19.14+
```

## Advanced Usage

### Adding New Exchanges

1. Implement WebSocket handler in `python/data_sources/ws_stream.py`
2. Add exchange identifier to `cross_exchange.py`
3. Update edge generation logic in `Graph.cpp`

### Custom Algorithms

Replace Bellman-Ford in `cpp/src/Graph.cpp` with:

- Floyd-Warshall (for all-pairs shortest paths)
- Johnson's algorithm (for sparse graphs)
- Custom cycle detection heuristics

### Performance Tuning

- Adjust `BUFFER_SIZE` for network throughput
- Enable C++ optimizations: `-O3 -march=native`
- Use release builds (remove debug symbols)

## Documentation

- [architecture.md](docs/architecture.md) - Detailed system architecture
- [usage_guide.md](docs/usage_guide.md) - Extended usage examples

## License

This project is intended for educational and research purposes.

## Disclaimer

**This software is for research and educational purposes only.** Cryptocurrency trading involves substantial risk. The authors are not responsible for any financial losses incurred through the use of this software. Always conduct thorough testing and risk assessment before deploying any trading system.