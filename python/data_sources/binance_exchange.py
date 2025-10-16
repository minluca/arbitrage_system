import asyncio
import logging
import json
import websockets
from .exchange_base import ExchangeBase
from config.settings import CSV_FIELDS
from core.utils import now_ts
from data_sources.parsers import parse_binance
import asyncio

class BinanceExchange(ExchangeBase):
    async def fetch_symbols(self, client):
        url = "https://api.binance.com/api/v3/exchangeInfo"
        logging.info("Fetching Binance symbols...")
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            symbols = {item['symbol'] for item in data['symbols'] if item.get('status') == 'TRADING'}
            return symbols
        except Exception as e:
            logging.error(f"Error fetching Binance symbols: {e}")
            return {"BTCUSDT", "ETHUSDT"}

    async def fetch_initial_prices(self, client, valid_pairs):
        url = "https://api.binance.com/api/v3/ticker/24hr"
        logging.info("Fetching Binance initial prices...")
        try:
            resp = await client.get(url)
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
            return snapshot
        except Exception as e:
            logging.error(f"Error fetching Binance prices: {e}")
            return []

    async def stream_ws(self, updates_q, symbols):
        symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
        if not symbols:
            logging.warning("[Binance] No symbols to follow.")
            return

        streams = "/".join(f"{s.lower()}@ticker" for s in symbols)
        url = f"wss://stream.binance.com:9443/stream?streams={streams}"

        backoff = 1.0
        msg_count = 0
        while True:
            try:
                logging.info(f"[Binance] WS connection: {url}")
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=None
                ) as ws:
                    logging.info(f"[Binance] Connected.")
                    backoff = 1.0

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            update = parse_binance(msg)
                            if update:
                                await updates_q.put(update)
                                msg_count += 1

                                if msg_count % 500 == 0:
                                    logging.info(f"[Binance] Stream active, processed {msg_count} messages.")
                        except Exception as parse_err:
                            logging.debug(f"[Binance] Parse skip: {parse_err}")

            except asyncio.CancelledError:
                logging.info(f"[Binance] Task cancelled, closing producer...")
                raise
            except Exception as e:
                logging.warning(f"[Binance] WS error: {e} → retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
