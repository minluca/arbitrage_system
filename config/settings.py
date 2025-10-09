"""
Configurazioni globali del sistema di arbitraggio.
"""
from itertools import product

# Asset da monitorare
COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "SHIB", "DOT",
    "LTC", "LINK", "UNI", "BCH", "XLM", "ATOM", "FIL", "XTZ", "VET",
    "USDT", "USDC", "TUSD"
]

# Generazione coppie trading (esclude base==quote)
SYMBOLS = [f"{base}{quote}" for base, quote in product(COINS, COINS) if base != quote]

# Exchange supportati
EXCHANGES = ["Binance", "OKX"]

# Stablecoin
STABLECOINS = {"USDT", "USDC", "TUSD"}

# Parametri arbitraggio
PROFIT_THRESHOLD = 1.00005  # 0.005% minimo
MIN_CYCLE_LENGTH = 3
MAX_CYCLE_LENGTH = 10

# Output
OUTPUT_DIR = "output"
OUTPUT_FOLDER = "crypto_csv_output"  # per compatibilità con sistema esistente
SNAPSHOTS_DIR = f"{OUTPUT_DIR}/snapshots"
LOGS_DIR = f"{OUTPUT_DIR}/logs"
DEBUG_DIR = f"{OUTPUT_DIR}/debug"

# CSV
CSV_FIELDS = ["timestamp", "symbol", "base", "quote", "price", "volume", "exchange"]
