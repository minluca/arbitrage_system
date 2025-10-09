from core.utils import now_ts
from config.settings import STABLECOINS, EXCHANGES
import logging

def build_cross_exchange_bridges(asset: str, exchanges: list = None):
    # funzione che crea ponti cross-exchange reali
    # genera archi bidirezionali 1:1 per lo stesso asset su exchange diversi
    if exchanges is None:
        exchanges = EXCHANGES
    
    bridges = []
    
    # Crea ponti bidirezionali tra ogni coppia di exchange
    for i, exch1 in enumerate(exchanges):
        for exch2 in exchanges[i+1:]:  # evita duplicati
            # Ponte exch1 -> exch2
            bridges.append({
                "timestamp": now_ts(),
                "symbol": f"{asset}_{exch1}_to_{asset}_{exch2}",
                "base": f"{asset}_{exch1}",
                "quote": f"{asset}_{exch2}",
                "price": 1.0,  # trasferimento 1:1 (assumiamo costo nullo, zero fees)
                "volume": 1.0,
                "exchange": "Cross"  # flag per distinguere da archi di mercato
            })
            
            # Ponte exch2 -> exch1 (bidirezionale)
            bridges.append({
                "timestamp": now_ts(),
                "symbol": f"{asset}_{exch2}_to_{asset}_{exch1}",
                "base": f"{asset}_{exch2}",
                "quote": f"{asset}_{exch1}",
                "price": 1.0,
                "volume": 1.0,
                "exchange": "Cross"
            })
    
    return bridges

def get_all_cross_exchange_bridges(assets: list):
    # genera tutti i ponti cross-exchange per una lista di asset
    # da chiamare dall'avvio, non ad ogni update
    all_bridges = []
    
    for asset in assets:
        bridges = build_cross_exchange_bridges(asset)
        all_bridges.extend(bridges)

    return all_bridges