import asyncio
import json
import logging
import websockets

from data_sources.parsers import parse_binance, parse_okx, to_okx_format

async def stream_ws(updates_q, url: str, subscribe_msg, parse_func, name: str):
    backoff = 1.0
    msg_count = 0
    while True:
        try:
            logging.info(f"[{name}] Connessione WS: {url}")
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                max_size=None
            ) as ws:
                logging.info(f"[{name}] Connesso.")
                backoff = 1.0

                if subscribe_msg:
                    await ws.send(json.dumps(subscribe_msg))
                    logging.info(f"[{name}] Messaggio di sottoscrizione inviato.")

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        update = parse_func(msg)
                        if update:
                            await updates_q.put(update)
                            msg_count += 1

                            if msg_count % 500 == 0:
                                logging.info(f"[{name}] Stream attivo, processati {msg_count} messaggi.")
                    except Exception as parse_err:
                        logging.debug(f"[{name}] Parse skip: {parse_err}")

        except asyncio.CancelledError:
            logging.info(f"[{name}] Task cancellato, chiusura producer...")
            raise
        except Exception as e:
            logging.warning(f"[{name}] Errore WS: {e} → retry in {backoff:.1f}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


async def stream_binance_ws(updates_q, symbols: list[str]):
    symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
    if not symbols:
        logging.warning("[Binance] Nessun simbolo da seguire.")
        return

    streams = "/".join(f"{s.lower()}@ticker" for s in symbols)
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"
    await stream_ws(updates_q, url, subscribe_msg=None, parse_func=parse_binance, name="Binance")


async def stream_okx_ws(updates_q, symbols: list[str]):
    symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
    inst_ids = [to_okx_format(s) for s in symbols if s]
    if not inst_ids:
        logging.warning("[OKX] Nessun simbolo da seguire.")
        return

    url = "wss://ws.okx.com:8443/ws/v5/public"
    sub_msg = {
        "op": "subscribe",
        "args": [{"channel": "tickers", "instId": inst} for inst in inst_ids],
    }
    await stream_ws(updates_q, url, subscribe_msg=sub_msg, parse_func=parse_okx, name="OKX")