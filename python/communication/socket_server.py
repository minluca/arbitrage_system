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
    logging.info("[Python Server] Invio ponti cross-exchange iniziali...")
    
    bridges = get_all_cross_exchange_bridges(assets)
        
    for bridge in bridges:
        _send_message(conn, bridge)
    
    logging.info(f"[Python Server] Inviati {len(bridges)} ponti cross-exchange")

async def socket_consumer(q: asyncio.Queue, common_assets: list = None):
    if common_assets is None:
        from config.settings import COINS
        common_assets = COINS 
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)

    print(f"[Python Server] In attesa di connessione su {HOST}:{PORT}...")
    conn, addr = s.accept()
    print(f"[Python Server] Connesso da {addr}")

    try:
        await send_initial_bridges(conn, common_assets)
        
        while True:
            update = await q.get()
            
            _send_message(conn, update)
            
            logging.debug(f"[Python Server] Inviato: {update['base']} -> {update['quote']} @ {update['price']} ({update['exchange']})")
            
            q.task_done()

    except Exception as e:
        logging.error(f"[Python Server] Errore: {e}")
    finally:
        conn.close()
        s.close()