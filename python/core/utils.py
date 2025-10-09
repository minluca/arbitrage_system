"""
Utility generiche per il progetto arbitrage_system.
"""
from datetime import datetime
import os
from config.settings import OUTPUT_FOLDER, COINS

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def now_ts() -> str:
    """Restituisce timestamp corrente con millisecondi."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def norm_symbol(s: str) -> str:
    """Normalizza simboli rimuovendo trattini: 'BTC-USDT' -> 'BTCUSDT'."""
    return s.replace("-", "").upper()


def split_symbol(symbol: str) -> tuple[str, str]:
    """Separa un simbolo in base e quote usando la lista COINS."""
    for coin in COINS:
        if symbol.endswith(coin):
            return symbol[:-len(coin)], coin
    return symbol, ""
