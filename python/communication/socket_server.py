import asyncio
import socket
import json
import logging
from config.settings import CSV_FIELDS
from config.network import HOST, PORT
from core.cross_exchange import get_all_cross_exchange_bridges

def _send_message(conn, data: dict):
    msg = json.dumps(data)
    msg_size = str(len(msg)).zfill(16).encode()
    conn.sendall(msg_size)
    conn.sendall(msg.encode())


async def send_initial_bridges(conn, assets: list):
    logging.info("[Python Server] Sending initial cross-exchange bridges...")
    
    bridges = get_all_cross_exchange_bridges(assets)
        
    for bridge in bridges:
        _send_message(conn, bridge)
    
    logging.info(f"[Python Server] Sent {len(bridges)} cross-exchange bridges")

async def socket_consumer(q: asyncio.Queue, common_assets: list = None):
    if common_assets is None:
        from config.settings import COINS
        common_assets = COINS 
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)

    print(f"[Python Server] Waiting for connection on {HOST}:{PORT}...")
    conn, addr = s.accept()
    print(f"[Python Server] Connected from {addr}")

    try:
        await send_initial_bridges(conn, common_assets)
        
        while True:
            update = await q.get()
            
            _send_message(conn, update)
            
            logging.debug(f"[Python Server] Sent: {update['base']} -> {update['quote']} @ {update['price']} ({update['exchange']})")
            
            q.task_done()

    except Exception as e:
        logging.error(f"[Python Server] Error: {e}")
    finally:
        conn.close()
        s.close()