import logging
from core.utils import now_ts
from config.settings import CSV_FIELDS

async def get_binance_symbols(client):
    url = "https://api.binance.com/api/v3/exchangeInfo"
    logging.info("Richiesta simboli Binance...")
    try:
        resp = await client.get(url)
        logging.info(f"Risposta Binance exchangeInfo: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        symbols = {item['symbol'] for item in data['symbols'] if item.get('status') == 'TRADING'}
        logging.info(f"Simboli Binance ottenuti: {len(symbols)}")
        return symbols
    except Exception as e:
        logging.error(f"Errore fetch simboli Binance: {e}")
        return {"BTCUSDT", "ETHUSDT"}

async def get_okx_symbols(client):
    url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
    logging.info("Richiesta simboli OKX...")
    try:
        resp = await client.get(url)
        logging.info(f"Risposta OKX instruments: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        symbols = {item['instId'].replace("-", "") for item in data['data'] if item.get('state') == 'live'}
        logging.info(f"Simboli OKX ottenuti: {len(symbols)}")
        return symbols
    except Exception as e:
        logging.error(f"Errore fetch simboli OKX: {e}")
        return {"BTCUSDT", "ETHUSDT"}

async def get_initial_binance_prices(client, valid_pairs):
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
                    CSV_FIELDS[0]: now_ts(),
                    CSV_FIELDS[1]: symbol,
                    CSV_FIELDS[4]: float(item['lastPrice']),
                    CSV_FIELDS[5]: float(item['volume']),
                    CSV_FIELDS[6]: 'Binance',
            })
        logging.info(f"Snapshot Binance ottenuto: {len(snapshot)} record")
        return snapshot
    except Exception as e:
        logging.error(f"Errore snapshot Binance: {e}")
        return []
    
async def get_initial_okx_prices(client, valid_pairs):
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
                    CSV_FIELDS[0]: now_ts(),
                    CSV_FIELDS[1]: symbol,
                    CSV_FIELDS[4]: float(item['last']),
                    CSV_FIELDS[5]: float(item['vol24h']),
                    CSV_FIELDS[6]: 'OKX',
             })
        logging.info(f"Snapshot OKX ottenuto: {len(snapshot)} record")
        return snapshot
    except Exception as e:
        logging.error(f"Errore snapshot OKX: {e}")
        return []