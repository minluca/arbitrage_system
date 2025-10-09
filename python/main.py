import asyncio
import logging
import os
import sys
import pandas as pd
import httpx

# Aggiungi la directory root al PYTHONPATH per permettere import assoluti
# Questo permette di importare config, python, etc. dalla root del progetto
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# import moduli
from data_sources.rest_api import get_binance_symbols, get_okx_symbols, get_initial_binance_prices, get_initial_okx_prices
from data_sources.ws_stream import stream_binance_ws, stream_okx_ws
from communication.socket_server import socket_consumer
from config.settings import OUTPUT_FOLDER, SYMBOLS, COINS

# logging config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_valid_pairs(client):
    # ottiene coppie valide
    binance_symbols, okx_symbols = await asyncio.gather(
        get_binance_symbols(client),
        get_okx_symbols(client),
    )
    valid_pairs_binance = [pair for pair in SYMBOLS if pair in binance_symbols]
    valid_pairs_okx = [pair for pair in SYMBOLS if pair in okx_symbols]
    return valid_pairs_binance, valid_pairs_okx

async def run_snapshot(client, valid_pairs_binance, valid_pairs_okx):
    # crea i due snapshot iniziali
    snapshot_binance, snapshot_okx = await asyncio.gather(
        get_initial_binance_prices(client, valid_pairs_binance),
        get_initial_okx_prices(client, valid_pairs_okx),
    )

    if snapshot_binance:
        df_binance = pd.DataFrame(snapshot_binance)
        df_binance.to_csv(os.path.join(OUTPUT_FOLDER, 'Initial_Snapshot_Binance.csv'), index=False)
        logging.info(f"Snapshot Binance salvato ({len(df_binance)} record)")

    if snapshot_okx:
        df_okx = pd.DataFrame(snapshot_okx)
        df_okx.to_csv(os.path.join(OUTPUT_FOLDER, 'Initial_Snapshot_OKX.csv'), index=False)
        logging.info(f"Snapshot OKX salvato ({len(df_okx)} record)")

async def run_live_stream(valid_pairs_binance, valid_pairs_okx):
    queue = asyncio.Queue()

    logging.info(f"[Binance] Avvio WS con {len(valid_pairs_binance)} simboli...")
    logging.info(f"[OKX] Avvio WS con {len(valid_pairs_okx)} simboli...")

    binance_task = asyncio.create_task(stream_binance_ws(queue, valid_pairs_binance))
    okx_task = asyncio.create_task(stream_okx_ws(queue, valid_pairs_okx))
    
    socket_task = asyncio.create_task(socket_consumer(queue, common_assets=COINS))

    tasks = [binance_task, okx_task, socket_task]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logging.info("CTRL+C rilevato, chiusura in corso...")
        raise

async def main():
    logging.info("Inizio script...")

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        # 1. fetch simboli
        valid_pairs_binance, valid_pairs_okx = await fetch_valid_pairs(client)

        # 2. snapshot iniziale + CSV
        await run_snapshot(client, valid_pairs_binance, valid_pairs_okx)

    # 3. avvio streaming live
    await run_live_stream(valid_pairs_binance, valid_pairs_okx)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Terminazione manuale con CTRL+C")