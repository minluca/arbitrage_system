# Cryptocurrency Arbitrage System - Usage Guide

This guide provides comprehensive instructions for compiling, running, configuring, and troubleshooting the arbitrage detection system.

---

## Table of Contents

1. [Compilation](#1-compilation)
2. [Execution](#2-execution)
3. [Configuration](#3-configuration)
4. [Troubleshooting](#4-troubleshooting)
5. [Output Files](#5-output-files)

---

## 1. Compilation

The C++ arbitrage detector must be compiled before first use.

### Windows (PowerShell)

```powershell
.\scripts\compile.ps1
```

Or manually using the correct paths:

```powershell
cd cpp
g++ -std=c++17 -O3 -o build/arbitrage_detector.exe src/main.cpp src/Graph.cpp src/SocketClient.cpp -Iinclude -lws2_32
```

**Note**: The `-lws2_32` flag is required on Windows for Winsock2 support.

### Linux/macOS

```bash
cd cpp
g++ -std=c++17 -O3 -o build/arbitrage_detector src/*.cpp -Iinclude -lpthread
```

**Note**: The `-lpthread` flag is required for POSIX thread support on Unix-like systems.

### Compilation Flags Explained

- **`-std=c++17`**: Enables C++17 standard features
- **`-O3`**: Maximum optimization for performance
- **`-Iinclude`**: Adds the include directory to search path
- **`-lws2_32`**: Links Windows Socket library (Windows only)
- **`-lpthread`**: Links POSIX threads library (Linux/macOS only)

### Verifying Compilation

After successful compilation, you should see:

```plaintext
cpp/build/arbitrage_detector.exe (Windows)
cpp/build/arbitrage_detector (Linux/macOS)
```

---

## 2. Execution

The system requires **two terminals** running simultaneously:

### Terminal 1: Python Server (Start First)

```bash
python python/main.py
```

**Expected output:**

```plaintext
2025-10-08 23:38:20 - INFO - Inizio script...
2025-10-08 23:38:20 - INFO - Snapshot Binance salvato (147 record)
2025-10-08 23:38:20 - INFO - Snapshot OKX salvato (132 record)
2025-10-08 23:38:20 - INFO - Snapshot Bybit salvato (98 record)
2025-10-08 23:38:20 - INFO - [Binance] Avvio WS con 147 simboli...
2025-10-08 23:38:20 - INFO - [OKX] Avvio WS con 132 simboli...
2025-10-08 23:38:20 - INFO - [Bybit] Avvio WS con 98 simboli...
[Python Server] In attesa di connessione su 127.0.0.1:5001...
[Python Server] Connesso da ('127.0.0.1', 52341)
2025-10-08 23:38:22 - INFO - [Python Server] Invio ponti cross-exchange iniziali...
2025-10-08 23:38:22 - INFO - [Python Server] Inviati 44 ponti cross-exchange
```

**What's happening:**

1. Python fetches initial market snapshots from Binance, OKX, and Bybit REST APIs
2. Saves snapshots to CSV files in `output/snapshots/`
3. Starts TCP server on `127.0.0.1:5001`
4. Waits for C++ client connection
5. Once connected, sends cross-exchange bridge edges (e.g., BTC_Binance ↔ BTC_OKX ↔ BTC_Bybit)
6. Begins streaming real-time WebSocket updates to the C++ client

### Terminal 2: C++ Detector (Start Second)

```bash
.\cpp\build\arbitrage_detector.exe
```

**Expected output:**

```plaintext
[warm-up] Ignoro arbitraggio per altri 3s @ 23:38:22
[warm-up] Ignoro arbitraggio per altri 2s @ 23:38:23
[warm-up] Ignoro arbitraggio per altri 1s @ 23:38:24
--- Nessun arbitraggio tra 23:38:25 e 23:38:26 ---
--- Nessun arbitraggio tra 23:38:26 e 23:38:27 ---
[2025-10-08 23:38:28] [!] Arbitraggio trovato! Profit = 1.0000673421x | Percorso: USDT_Binance -> BTC_Binance -> BTC_OKX -> USDT_OKX -> USDT_Binance
=== Arbitraggi trovati @ 23:38:28 => 1 ===
[2025-10-08 23:38:30] [!] Arbitraggio trovato! Profit = 1.0001234567x | Percorso: ETH_Binance -> USDT_Binance -> USDT_OKX -> ETH_OKX -> ETH_Binance
=== Arbitraggi trovati @ 23:38:30 => 1 ===
```

**What's happening:**

1. C++ client connects to Python server on `127.0.0.1:5001`
2. Receives initial cross-exchange bridges
3. Enters warm-up phase (3 seconds by default) to allow graph initialization
4. Begins receiving real-time price updates
5. Runs Bellman-Ford algorithm on each update to detect negative cycles
6. Outputs arbitrage opportunities with timestamp, profit factor, and path

### Stopping the System

Press **Ctrl+C** in either terminal to gracefully shut down:

```plaintext
2025-10-08 23:40:15 - INFO - Terminazione manuale con CTRL+C
```

---

## 3. Configuration

### 3.1 Trading Parameters (`config/settings.py`)

#### `COINS` - Assets to Monitor

```python
COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "SHIB", "DOT",
    "LTC", "LINK", "UNI", "BCH", "XLM", "ATOM", "FIL", "XTZ", "VET",
    "USDT", "USDC", "TUSD"
]
```

**Effect**:

- Determines which assets are included in trading pairs
- Total pairs = `len(COINS) * (len(COINS) - 1)` (all permutations except base=quote)
- Example: 22 coins = 462 pairs (22 × 21)

**Modification Example:**

Reduce to 5 coins for testing:

```python
COINS = ["BTC", "ETH", "USDT", "BNB", "SOL"]
```

**Result**:

- Pairs: 5 × 4 = 20 pairs
- Faster startup, less network traffic
- Fewer arbitrage opportunities detected

Add a new coin:

```python
COINS = [...existing..., "MATIC"]
```

**Result**:

- New pairs: `MATIC + existing coins` (43 new pairs if 22 existing)
- More cross-exchange bridges created
- Increased detection surface

#### `PROFIT_THRESHOLD` - Minimum Profit to Report

```python
PROFIT_THRESHOLD = 1.00005  # 0.005% minimum
```

**Effect**:

- Only cycles with `profit >= PROFIT_THRESHOLD` are reported
- Lower threshold = more opportunities (but more noise)
- Higher threshold = fewer, more significant opportunities

**Sensitivity vs. Noise Trade-off:**

| Threshold | Profit % | Behavior |
|-----------|----------|----------|
| `1.00001` | 0.001% | Very noisy, many false positives due to bid-ask spread fluctuations |
| `1.00005` | 0.005% | Balanced - catches real micro-opportunities |
| `1.0001` | 0.01% | Conservative - only clear opportunities |
| `1.001` | 0.1% | Very rare - significant market inefficiencies only |

#### `MIN_CYCLE_LENGTH` and `MAX_CYCLE_LENGTH`

```python
MIN_CYCLE_LENGTH = 3
MAX_CYCLE_LENGTH = 10
```

**Effect**:

- `MIN_CYCLE_LENGTH`: Minimum edges in arbitrage cycle (typically 3+)
- `MAX_CYCLE_LENGTH`: Maximum edges to report (prevents overly complex paths)

**Note**: In current implementation, `MAX_CYCLE_LENGTH` is used for filtering. Shorter cycles (3-4 hops) are generally more profitable due to lower cumulative fees.

**Example:**

Only show simple triangular arbitrage:

```python
MIN_CYCLE_LENGTH = 3
MAX_CYCLE_LENGTH = 4
```

### 3.2 Network Settings (`config/network.py`)

#### `HOST` and `PORT` - TCP Server Address

```python
HOST = "127.0.0.1"
PORT = 5001
```

**Effect**:

- Python server listens on this address
- C++ client connects to this address
- Change `PORT` if 5001 is already in use

**Example:**

Run on different port:

```python
PORT = 5555
```

Then update C++ code ([cpp/src/main.cpp:6](../cpp/src/main.cpp#L6)):

```cpp
Socket::Client client("127.0.0.1", 5555);
```

#### `WS_PING_INTERVAL` - WebSocket Keep-Alive

```python
WS_PING_INTERVAL = 20  # seconds
```

**Effect**:

- How often to send ping frames to keep WebSocket connections alive
- Prevents timeout disconnections from exchanges
- Lower values = more overhead, higher reliability

**Example:**

For unstable connections:

```python
WS_PING_INTERVAL = 10  # More frequent pings
```

#### `WS_RECONNECT_DELAY` - Reconnection Backoff

```python
WS_RECONNECT_DELAY = 1.0      # Initial delay
WS_MAX_RECONNECT_DELAY = 30.0 # Maximum delay
```

**Effect**:

- Initial wait before reconnecting after WebSocket failure
- Exponential backoff up to `WS_MAX_RECONNECT_DELAY`
- Prevents hammering exchanges during outages

---

## 4. Troubleshooting

### 4.1 Port Already in Use

**Error:**

```plaintext
OSError: [Errno 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted
```

**Cause**: Another process is using port 5001.

**Solution 1**: Identify and kill the process

Windows:

```powershell
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

Example:

```powershell
> netstat -ano | findstr :5001
  TCP    127.0.0.1:5001         0.0.0.0:0              LISTENING       12345

> taskkill /PID 12345 /F
SUCCESS: The process with PID 12345 has been terminated.
```

Linux/macOS:

```bash
lsof -i :5001
kill -9 <PID>
```

**Solution 2**: Change the port in both files

[config/network.py](../config/network.py):

```python
PORT = 5002
```

[cpp/src/main.cpp:6](../cpp/src/main.cpp#L6):

```cpp
Socket::Client client("127.0.0.1", 5002);
```

Then recompile the C++ client.

### 4.2 Connection Refused

**Error (C++ side):**

```plaintext
Connection failed or recv error
```

**Cause**: C++ client started before Python server, or firewall blocking connection.

**Solution 1**: Ensure correct startup order

1. **First**: Start Python server (`python python/main.py`)
2. Wait for: `[Python Server] In attesa di connessione su 127.0.0.1:5001...`
3. **Then**: Start C++ client (`.\cpp\build\arbitrage_detector.exe`)

**Solution 2**: Check firewall settings

Windows Firewall may block localhost connections. Temporarily disable or add exception:

```powershell
# Add firewall rule
netsh advfirewall firewall add rule name="Arbitrage System" dir=in action=allow protocol=TCP localport=5001
```

**Solution 3**: Verify server is listening

```powershell
netstat -ano | findstr :5001
```

Should show `LISTENING` state.

### 4.3 No Arbitrage Detected

**Symptom**: System runs but never prints arbitrage opportunities.

**Possible Causes:**

#### Cause 1: Profit threshold too high

**Solution**: Lower `PROFIT_THRESHOLD` in [config/settings.py](../config/settings.py):

```python
PROFIT_THRESHOLD = 1.000001  # Very sensitive
```

Restart Python server to apply changes.

#### Cause 2: Insufficient assets

**Solution**: Increase `COINS` list to create more trading paths:

```python
COINS = ["BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX"]
```

More assets → more pairs → more cross-exchange bridges → higher detection probability.

#### Cause 3: WebSocket not receiving updates

**Solution**: Check Python logs for WebSocket messages:

Enable debug logging in [python/main.py:15](../python/main.py#L15):

```python
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

Look for:

```plaintext
DEBUG - [Python Server] Inviato: BTC -> USDT @ 123456.78 (Binance)
```

If no debug messages appear, WebSocket connections may have failed (see section 4.4).

#### Cause 4: Market efficiency

**Reality**: Real markets are highly efficient. Arbitrage opportunities are:

- Rare (seconds to minutes between occurrences)
- Small (0.01-0.1% profit typical)
- Short-lived (milliseconds)

This is expected behavior. Consider:

- Running for 5-10 minutes before expecting results
- Lowering threshold during low-volatility periods
- Checking logs for "No arbitrage" messages (confirms system is working)

### 4.4 WebSocket Connection Failures

**Error:**

```plaintext
ERROR - WebSocket connection failed: ...
INFO - Reconnecting in 1.0 seconds...
```

**Possible Causes:**

#### Cause 1: No internet connection

**Solution**: Verify connectivity:

```bash
ping binance.com
ping okx.com
```

#### Cause 2: Exchange API down or maintenance

**Solution**: Check exchange status pages:

- Binance: <https://www.binance.com/en/support/announcement>
- OKX: <https://www.okx.com/support/hc/en-us>
- Bybit: <https://www.bybit.com/en/announcement-info>

Wait for maintenance to complete.

#### Cause 3: Rate limiting

**Symptom**: Connections drop after initial success.

**Solution**: Reduce request frequency or number of symbols:

```python
COINS = ["BTC", "ETH", "USDT", "BNB", "SOL"]  # Fewer coins = fewer WS streams
```

#### Cause 4: Firewall/proxy blocking WebSocket

**Solution**:

Windows:

```powershell
# Temporarily disable firewall for testing
netsh advfirewall set allprofiles state off
```

Corporate networks: Contact IT to whitelist `*.binance.com` and `*.okx.com` on ports 443/9443.

### 4.5 Compilation Errors

#### Error: `'std::optional' is not a member of 'std'`

**Cause**: C++17 features not enabled.

**Solution**: Verify `-std=c++17` flag and compiler version:

```bash
g++ --version  # Should be GCC 7.0+ or Clang 5.0+
```

Update compiler if necessary:

Windows (MSYS2):

```bash
pacman -Syu mingw-w64-x86_64-gcc
```

Ubuntu:

```bash
sudo apt install g++-9
```

#### Error: `undefined reference to 'WSAStartup'`

**Cause**: Missing Winsock2 library on Windows.

**Solution**: Add `-lws2_32` flag:

```bash
g++ ... -lws2_32
```

#### Error: `json.hpp: No such file or directory`

**Cause**: Include path not set correctly.

**Solution**: Verify `nlohmann/json.hpp` exists in `cpp/include/` and use `-Iinclude` flag:

```bash
g++ ... -Iinclude
```

Or specify absolute path:

```bash
g++ ... -I/full/path/to/cpp/include
```

---

## 5. Output Files

### 5.1 Initial Snapshots

**Location**: `output/snapshots/`

**Files**:

- `Initial_Snapshot_Binance.csv`
- `Initial_Snapshot_OKX.csv`
- `Initial_Snapshot_Bybit.csv`

**Format**:

```csv
timestamp,symbol,price,volume,exchange
2025-10-08 23:38:20.621,ETHBTC,0.0367,15166.0629,Binance
2025-10-08 23:38:20.621,LTCBTC,0.000959,9435.997,Binance
2025-10-08 23:38:20.622,BNBBTC,0.010624,58732.915,Binance
2025-10-08 23:38:20.622,BNBETH,0.2894,15361.485,Binance
2025-10-08 23:38:20.622,BTCUSDT,123307.37,17635.966,Binance
2025-10-08 23:38:20.622,ETHUSDT,4525.59,419281.8823,Binance
```

**Columns**:

| Column | Description | Example |
|--------|-------------|---------|
| `timestamp` | Snapshot creation time (millisecond precision) | `2025-10-08 23:38:20.621` |
| `symbol` | Trading pair symbol | `BTCUSDT` |
| `price` | Current price (quote currency) | `123307.37` |
| `volume` | 24-hour trading volume | `17635.966` |
| `exchange` | Exchange name | `Binance` or `OKX` |

**Interpreting Data**:

Example row:

```plaintext
2025-10-08 23:38:20.622,BTCUSDT,123307.37,17635.966,Binance
```

This means:

- 1 BTC = 123,307.37 USDT on Binance
- 24h volume: 17,635.966 BTC traded
- Snapshot taken at 23:38:20.622

**Use Cases**:

- Initial market state verification
- Historical analysis
- Debugging graph initialization

### 5.2 Real-Time Console Output

**Format**:

```plaintext
[2025-10-08 23:38:28] [!] Arbitraggio trovato! Profit = 1.0000673421x | Percorso: USDT_Binance -> BTC_Binance -> BTC_OKX -> USDT_OKX -> USDT_Binance
```

**Components**:

- **Timestamp**: `[2025-10-08 23:38:28]` - When arbitrage was detected
- **Profit Factor**: `1.0000673421x` - Multiply initial capital by this (1.0000673421 = 0.0067% profit)
- **Path**: `A -> B -> C -> ... -> A` - Sequence of conversions

**Interpreting Profit**:

| Profit Factor | Percentage | Interpretation |
|---------------|------------|----------------|
| `1.0000673421x` | 0.0067% | Micro-arbitrage, likely unprofitable after fees |
| `1.0005x` | 0.05% | Small opportunity, marginally profitable |
| `1.001x` | 0.1% | Significant opportunity |
| `1.01x` | 1.0% | Major market inefficiency (rare) |

**Example Path Breakdown**:

```plaintext
USDT_Binance -> BTC_Binance -> BTC_OKX -> USDT_OKX -> USDT_Binance
```

1. Start with USDT on Binance
2. Buy BTC on Binance (USDT → BTC)
3. Transfer BTC to OKX (cross-exchange bridge)
4. Sell BTC for USDT on OKX (BTC → USDT)
5. Transfer USDT back to Binance (cross-exchange bridge)
6. End with more USDT than you started

### 5.3 Logs Directory

**Location**: `output/logs/` (if configured)

Currently, the system logs to console. To enable file logging, modify [python/main.py:15](../python/main.py#L15):

```python
import os
os.makedirs("output/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/logs/arbitrage.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
```

---

## Summary

This guide covered:

1. **Compilation** for Windows/Linux/macOS
2. **Execution** steps with expected output examples
3. **Configuration** of trading parameters and network settings
4. **Troubleshooting** common errors with concrete solutions
5. **Output files** interpretation and usage
6. **Performance tuning** with measured metrics
7. **Advanced use cases** including new exchanges, algorithm modifications, custom logging, and backtesting

For architectural details, see [architecture.md](architecture.md).
