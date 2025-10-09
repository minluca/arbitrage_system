import logging
from core.utils import now_ts
from config.settings import CSV_FIELDS

async def get_binance_symbols(client):
    # fetch lista simboli da Binance (endpoint exchangeInfo)
    url = "https://api.binance.com/api/v3/exchangeInfo"
    logging.info("Richiesta simboli Binance...")
    try:
        resp = await client.get(url)
        logging.info(f"Risposta Binance exchangeInfo: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        # filtriamo simboli attivi con status = TRADING
        symbols = {item['symbol'] for item in data['symbols'] if item.get('status') == 'TRADING'}
        logging.info(f"Simboli Binance ottenuti: {len(symbols)}")
        return symbols
    except Exception as e:
        # intercetta errori, fallback con simboli default
        logging.error(f"Errore fetch simboli Binance: {e}")
        return {"BTCUSDT", "ETHUSDT"}

async def get_okx_symbols(client):
    # fetch lista simboli da OKX (endpoint instruments spot)
    url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
    logging.info("Richiesta simboli OKX...")
    try:
        resp = await client.get(url)
        logging.info(f"Risposta OKX instruments: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        # rimuoviamo il trattino (es. BTC-USDT → BTCUSDT)
        symbols = {item['instId'].replace("-", "") for item in data['data'] if item.get('state') == 'live'}
        logging.info(f"Simboli OKX ottenuti: {len(symbols)}")
        return symbols
    except Exception as e:
        # intercetta errori, fallback con simboli default
        logging.error(f"Errore fetch simboli OKX: {e}")
        return {"BTCUSDT", "ETHUSDT"}

async def get_initial_binance_prices(client, valid_pairs):
    # snapshot iniziale prezzi/volumi da Binance
    url = "https://api.binance.com/api/v3/ticker/24hr"
    logging.info("Richiesta snapshot Binance...")
    try:
        resp = await client.get(url)
        logging.info(f"Risposta Binance snapshot: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        snapshot = []
        for item in data:
            symbol = item['symbol']
            if symbol in valid_pairs:
                snapshot.append({
                    CSV_FIELDS[0]: now_ts(),                     # timestamp
                    CSV_FIELDS[1]: symbol,                       # symbol
                    CSV_FIELDS[4]: float(item['lastPrice']),     # price
                    CSV_FIELDS[5]: float(item['volume']),        # volume
                    CSV_FIELDS[6]: 'Binance',                    # exchange
            })
        logging.info(f"Snapshot Binance ottenuto: {len(snapshot)} record")
        return snapshot
    except Exception as e:
        logging.error(f"Errore snapshot Binance: {e}")
        return []
    
async def get_initial_okx_prices(client, valid_pairs):
    # snapshot iniziale prezzi/volumi da OKX
    url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    logging.info("Richiesta snapshot OKX...")
    try:
        resp = await client.get(url)
        logging.info(f"Risposta OKX snapshot: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        snapshot = []
        for item in data['data']:
            symbol = item['instId'].replace("-", "")
            if symbol in valid_pairs:
                snapshot.append({
                    CSV_FIELDS[0]: now_ts(),                 # timestamp
                    CSV_FIELDS[1]: symbol,                   # symbol
                    CSV_FIELDS[4]: float(item['last']),      # price
                    CSV_FIELDS[5]: float(item['vol24h']),    # volume
                    CSV_FIELDS[6]: 'OKX',                    # exchange
             })
        logging.info(f"Snapshot OKX ottenuto: {len(snapshot)} record")
        return snapshot
    except Exception as e:
        logging.error(f"Errore snapshot OKX: {e}")
        return []