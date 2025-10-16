import asyncio
import logging
import json
import websockets
from .exchange_base import ExchangeBase
from config.settings import CSV_FIELDS
from core.utils import now_ts
from data_sources.parsers import parse_bybit

class BybitExchange(ExchangeBase):
    async def fetch_symbols(self, client):
        url = "https://api.bybit.com/v5/market/instruments-info?category=spot"
        logging.info("Fetching Bybit symbols...")
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            symbols = {item['symbol'] for item in data['result']['list'] if item.get('status') == 'Trading'}
            return symbols
        except Exception as e:
            logging.error(f"Error fetching Bybit symbols: {e}")
            return {"BTCUSDT", "ETHUSDT"}

    async def fetch_initial_prices(self, client, valid_pairs):
        url = "https://api.bybit.com/v5/market/tickers?category=spot"
        logging.info("Fetching Bybit initial prices...")
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            snapshot = []
            for item in data['result']['list']:
                symbol = item['symbol']
                if symbol in valid_pairs:
                    snapshot.append({
                        CSV_FIELDS[0]: now_ts(),
                        CSV_FIELDS[1]: symbol,
                        CSV_FIELDS[4]: float(item['lastPrice']),
                        CSV_FIELDS[5]: float(item['volume24h']),
                        CSV_FIELDS[6]: 'Bybit',
                    })
            return snapshot
        except Exception as e:
            logging.error(f"Error fetching Bybit prices: {e}")
            return []

    async def stream_ws(self, updates_q, symbols):
        symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
        if not symbols:
            logging.warning("[Bybit] No symbols to follow.")
            return

        url = "wss://stream.bybit.com/v5/public/spot"

        ticker_args = [f"tickers.{s}" for s in symbols]
        batch_size = 10
        sub_messages = []
        for i in range(0, len(ticker_args), batch_size):
            batch = ticker_args[i:i+batch_size]
            sub_messages.append({
                "op": "subscribe",
                "args": batch
            })
        logging.info(f"[Bybit] Preparing {len(sub_messages)} subscriptions for {len(ticker_args)} tickers")

        backoff = 1.0
        msg_count = 0
        while True:
            try:
                logging.info(f"[Bybit] WS connection: {url}")
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=None
                ) as ws:
                    logging.info(f"[Bybit] Connected.")
                    backoff = 1.0

                    for sub_msg in sub_messages:
                        await ws.send(json.dumps(sub_msg))
                        await asyncio.sleep(0.1)
                    logging.info(f"[Bybit] {len(sub_messages)} subscription messages sent.")

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            update = parse_bybit(msg)
                            if update:
                                await updates_q.put(update)
                                msg_count += 1
                                if msg_count % 500 == 0:
                                    logging.info(f"[Bybit] Stream active, processed {msg_count} messages.")
                        except Exception as parse_err:
                            logging.debug(f"[Bybit] Parse skip: {parse_err}")
            except asyncio.CancelledError:
                logging.info(f"[Bybit] Task cancelled, closing producer...")
                raise
            except Exception as e:
                logging.warning(f"[Bybit] WS error: {e} → retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
