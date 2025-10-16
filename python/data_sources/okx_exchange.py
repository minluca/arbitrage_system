import asyncio
import logging
import json
import websockets
from .exchange_base import ExchangeBase
from config.settings import CSV_FIELDS
from core.utils import now_ts
from data_sources.parsers import parse_okx, to_okx_format

class OKXExchange(ExchangeBase):
    async def fetch_symbols(self, client):
        url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
        logging.info("Fetching OKX symbols...")
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            symbols = {item['instId'].replace("-", "") for item in data['data'] if item.get('state') == 'live'}
            return symbols
        except Exception as e:
            logging.error(f"Error fetching OKX symbols: {e}")
            return {"BTCUSDT", "ETHUSDT"}

    async def fetch_initial_prices(self, client, valid_pairs):
        url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
        logging.info("Fetching OKX initial prices...")
        try:
            resp = await client.get(url)
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
            return snapshot
        except Exception as e:
            logging.error(f"Error fetching OKX prices: {e}")
            return []

    async def stream_ws(self, updates_q, symbols):
        symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
        inst_ids = [to_okx_format(s) for s in symbols if s]
        if not inst_ids:
            logging.warning("[OKX] No symbols to follow.")
            return

        url = "wss://ws.okx.com:8443/ws/v5/public"
        sub_msg = {
            "op": "subscribe",
            "args": [{"channel": "tickers", "instId": inst} for inst in inst_ids],
        }

        backoff = 1.0
        msg_count = 0
        while True:
            try:
                logging.info(f"[OKX] WS connection: {url}")
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=None
                ) as ws:
                    logging.info(f"[OKX] Connected.")
                    backoff = 1.0

                    await ws.send(json.dumps(sub_msg))
                    logging.info(f"[OKX] Subscription message sent.")

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            update = parse_okx(msg)
                            if update:
                                await updates_q.put(update)
                                msg_count += 1
                                if msg_count % 500 == 0:
                                    logging.info(f"[OKX] Stream active, processed {msg_count} messages.")
                        except Exception as parse_err:
                            logging.debug(f"[OKX] Parse skip: {parse_err}")
            except asyncio.CancelledError:
                logging.info(f"[OKX] Task cancelled, closing producer...")
                raise
            except Exception as e:
                logging.warning(f"[OKX] WS error: {e} → retry in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
