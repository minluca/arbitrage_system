"""
Configurazioni di rete per comunicazione Python-C++.
"""

# Socket TCP
HOST = "127.0.0.1"
PORT = 5001

# Timeout
SOCKET_TIMEOUT = 30  # secondi
CONNECT_TIMEOUT = 5  # secondi

# WebSocket
WS_PING_INTERVAL = 20
WS_PING_TIMEOUT = 20
WS_RECONNECT_DELAY = 1.0
WS_MAX_RECONNECT_DELAY = 30.0
