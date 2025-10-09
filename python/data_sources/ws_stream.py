import asyncio
import json
import logging
import websockets

from data_sources.parsers import parse_binance, parse_okx, to_okx_format

async def stream_ws(updates_q, url: str, subscribe_msg, parse_func, name: str):
    # funzione generica WebSocket per gestire connessione, parsing e retry
    # ogni exchange passa la sua url, eventuale messaggio di sub e parser dedicato
    backoff = 1.0
    msg_count = 0       # contatore msg per logging
    while True:
        try:
            logging.info(f"[{name}] Connessione WS: {url}")
            async with websockets.connect(
                url,
                ping_interval=20,   # keepalive periodico
                ping_timeout=20,    # timeout se non riceviamo risposte al ping
                max_size=None       # accetta stream grandi
            ) as ws:
                logging.info(f"[{name}] Connesso.")
                backoff = 1.0   # reset del backoff dopo connessione riuscita

                # OKX richiede un messaggio di sottoscrizione
                if subscribe_msg:
                    await ws.send(json.dumps(subscribe_msg))
                    logging.info(f"[{name}] Messaggio di sottoscrizione inviato.")

                # loop principale: ascolta continuamente i messaggi dallo stream
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        update = parse_func(msg)    # parsing con funzione custom dell’exchange
                        if update:
                            await updates_q.put(update)   # se valido, pusha in coda
                            msg_count += 1

                            if msg_count % 500 == 0:
                                logging.info(f"[{name}] Stream attivo, processati {msg_count} messaggi.")
                    except Exception as parse_err:
                        logging.debug(f"[{name}] Parse skip: {parse_err}")  # intercetta msg anomali

        except asyncio.CancelledError:
            logging.info(f"[{name}] Task cancellato, chiusura producer...")  # intercetta CTRL+C
            raise
        except Exception as e:
            logging.warning(f"[{name}] Errore WS: {e} → retry in {backoff:.1f}s")
            await asyncio.sleep(backoff)             # attesa prima del retry
            backoff = min(backoff * 2, 30.0)         # backoff esponenziale, max 30s


async def stream_binance_ws(updates_q, symbols: list[str]):
    # WS Binance - non usa sottoscrizione
    # formnato: 'btcusdt@ticker'
    symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
    if not symbols:
        logging.warning("[Binance] Nessun simbolo da seguire.")
        return

    streams = "/".join(f"{s.lower()}@ticker" for s in symbols)  # stream multipli separati da "/"
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"
    await stream_ws(updates_q, url, subscribe_msg=None, parse_func=parse_binance, name="Binance")


async def stream_okx_ws(updates_q, symbols: list[str]):
    # WS OKX - richiede sottoscrizione
    symbols = [s for s in (symbols or []) if isinstance(s, str) and s.strip()]
    inst_ids = [to_okx_format(s) for s in symbols if s]
    if not inst_ids:
        logging.warning("[OKX] Nessun simbolo da seguire.")
        return

    url = "wss://ws.okx.com:8443/ws/v5/public"
    sub_msg = {
        "op": "subscribe",
        "args": [{"channel": "tickers", "instId": inst} for inst in inst_ids],  # un ticker per ogni coppia
    }
    await stream_ws(updates_q, url, subscribe_msg=sub_msg, parse_func=parse_okx, name="OKX")