"""
Configurazioni globali del sistema di arbitraggio.
"""
from itertools import product

COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "SHIB", "DOT",
    "LTC", "LINK", "UNI", "BCH", "XLM", "ATOM", "FIL", "XTZ", "VET",
    "USDT", "USDC", "TUSD"
]

SYMBOLS = [f"{base}{quote}" for base, quote in product(COINS, COINS) if base != quote]

EXCHANGES = ["Binance", "OKX"]

STABLECOINS = {"USDT", "USDC", "TUSD"}

PROFIT_THRESHOLD = 1.00005
MIN_CYCLE_LENGTH = 3
MAX_CYCLE_LENGTH = 10

OUTPUT_DIR = "output"
OUTPUT_FOLDER = "crypto_csv_output"
SNAPSHOTS_DIR = f"{OUTPUT_DIR}/snapshots"
LOGS_DIR = f"{OUTPUT_DIR}/logs"
DEBUG_DIR = f"{OUTPUT_DIR}/debug"

CSV_FIELDS = ["timestamp", "symbol", "base", "quote", "price", "volume", "exchange"]
