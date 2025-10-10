import asyncio
import logging
import os
import sys
import pandas as pd
import httpx

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_sources.binance_exchange import BinanceExchange
from data_sources.okx_exchange import OKXExchange
from data_sources.bybit_exchange import BybitExchange
from communication.socket_server import socket_consumer
from config.settings import SNAPSHOTS_DIR, SYMBOLS, COINS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_valid_pairs(client, exchanges):
    binance_symbols, okx_symbols, bybit_symbols = await asyncio.gather(
        exchanges['binance'].fetch_symbols(client),
        exchanges['okx'].fetch_symbols(client),
        exchanges['bybit'].fetch_symbols(client),
    )
    valid_pairs_binance = [pair for pair in SYMBOLS if pair in binance_symbols]
    valid_pairs_okx = [pair for pair in SYMBOLS if pair in okx_symbols]
    valid_pairs_bybit = [pair for pair in SYMBOLS if pair in bybit_symbols]
    return valid_pairs_binance, valid_pairs_okx, valid_pairs_bybit

async def run_snapshot(client, exchanges, valid_pairs_binance, valid_pairs_okx, valid_pairs_bybit):
    snapshot_binance, snapshot_okx, snapshot_bybit = await asyncio.gather(
        exchanges['binance'].fetch_initial_prices(client, valid_pairs_binance),
        exchanges['okx'].fetch_initial_prices(client, valid_pairs_okx),
        exchanges['bybit'].fetch_initial_prices(client, valid_pairs_bybit),
    )

    if snapshot_binance:
        df_binance = pd.DataFrame(snapshot_binance)
        df_binance.to_csv(os.path.join(SNAPSHOTS_DIR, 'Initial_Snapshot_Binance.csv'), index=False)
        logging.info(f"Snapshot Binance salvato ({len(df_binance)} record)")

    if snapshot_okx:
        df_okx = pd.DataFrame(snapshot_okx)
        df_okx.to_csv(os.path.join(SNAPSHOTS_DIR, 'Initial_Snapshot_OKX.csv'), index=False)
        logging.info(f"Snapshot OKX salvato ({len(df_okx)} record)")

    if snapshot_bybit:
        df_bybit = pd.DataFrame(snapshot_bybit)
        df_bybit.to_csv(os.path.join(SNAPSHOTS_DIR, 'Initial_Snapshot_Bybit.csv'), index=False)
        logging.info(f"Snapshot Bybit salvato ({len(df_bybit)} record)")

async def run_live_stream(exchanges, valid_pairs_binance, valid_pairs_okx, valid_pairs_bybit):
    queue = asyncio.Queue()

    logging.info(f"[Binance] Avvio WS con {len(valid_pairs_binance)} simboli...")
    logging.info(f"[OKX] Avvio WS con {len(valid_pairs_okx)} simboli...")
    logging.info(f"[Bybit] Avvio WS con {len(valid_pairs_bybit)} simboli...")

    binance_task = asyncio.create_task(exchanges['binance'].stream_ws(queue, valid_pairs_binance))
    okx_task = asyncio.create_task(exchanges['okx'].stream_ws(queue, valid_pairs_okx))
    bybit_task = asyncio.create_task(exchanges['bybit'].stream_ws(queue, valid_pairs_bybit))
    socket_task = asyncio.create_task(socket_consumer(queue, common_assets=COINS))

    tasks = [binance_task, okx_task, bybit_task, socket_task]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logging.info("CTRL+C rilevato, chiusura in corso...")
        raise

async def main():
    logging.info("Inizio script...")

    exchanges = {
        'binance': BinanceExchange(),
        'okx': OKXExchange(),
        'bybit': BybitExchange(),
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        valid_pairs_binance, valid_pairs_okx, valid_pairs_bybit = await fetch_valid_pairs(client, exchanges)
        await run_snapshot(client, exchanges, valid_pairs_binance, valid_pairs_okx, valid_pairs_bybit)

    await run_live_stream(exchanges, valid_pairs_binance, valid_pairs_okx, valid_pairs_bybit)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Terminazione manuale con CTRL+C")