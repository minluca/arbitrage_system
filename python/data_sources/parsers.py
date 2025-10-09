"""
Parsers per messaggi WebSocket e REST API da exchange crypto.
"""
from core.utils import now_ts, norm_symbol, split_symbol
from config.settings import CSV_FIELDS


def to_okx_format(s: str) -> str:
    """Converte simbolo da formato Binance a formato OKX (con trattino)."""
    if not s or not isinstance(s, str):
        return ""
    # split tra simboli - alcuni sono di 4 lettere, altri di 3
    if s.endswith(("USDT", "USDC", "TUSD")):
        return s[:-4] + "-" + s[-4:]
    else:
        return s[:-3] + "-" + s[-3:]


def parse_binance(msg):
    """Parser per messaggi WebSocket da Binance."""
    data = msg.get("data", msg)
    try:
        symbol = norm_symbol(data["s"])
        base, quote = split_symbol(symbol)
        return {
            CSV_FIELDS[0]: now_ts(),                # timestamp
            CSV_FIELDS[1]: norm_symbol(data["s"]),  # symbol
            CSV_FIELDS[2]: base,                    # base
            CSV_FIELDS[3]: quote,                   # quote
            CSV_FIELDS[4]: float(data["c"]),        # price
            CSV_FIELDS[5]: float(data["v"]),        # volume
            CSV_FIELDS[6]: "Binance"                # exchange
        }
    except Exception:
        return None     # messaggio anomalo


def parse_okx(msg):
    """Parser per messaggi WebSocket da OKX."""
    if "data" not in msg:
        return None
    try:
        item = msg["data"][0]  # lista con un ticker
        symbol = norm_symbol(item["instId"])
        base, quote = split_symbol(symbol)
        return {
            CSV_FIELDS[0]: now_ts(),                    # timestamp
            CSV_FIELDS[1]: norm_symbol(item["instId"]), # symbol
            CSV_FIELDS[2]: base,                        # base
            CSV_FIELDS[3]: quote,                       # quote
            CSV_FIELDS[4]: float(item["last"]),         # price
            CSV_FIELDS[5]: float(item["vol24h"]),       # volume
            CSV_FIELDS[6]: "OKX"                        # exchange
        }
    except Exception:
        return None     # messaggio anomalo
