from core.utils import now_ts, norm_symbol, split_symbol
from config.settings import CSV_FIELDS


def to_okx_format(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    if s.endswith(("USDT", "USDC", "TUSD")):
        return s[:-4] + "-" + s[-4:]
    else:
        return s[:-3] + "-" + s[-3:]


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


def parse_okx(msg):
    """Parser per messaggi WebSocket da OKX."""
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
