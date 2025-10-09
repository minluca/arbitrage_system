from core.utils import now_ts
from config.settings import STABLECOINS, EXCHANGES
import logging

def build_cross_exchange_bridges(asset: str, exchanges: list = None):
    if exchanges is None:
        exchanges = EXCHANGES
    
    bridges = []
    
    for i, exch1 in enumerate(exchanges):
        for exch2 in exchanges[i+1:]:
            bridges.append({
                "timestamp": now_ts(),
                "symbol": f"{asset}_{exch1}_to_{asset}_{exch2}",
                "base": f"{asset}_{exch1}",
                "quote": f"{asset}_{exch2}",
                "price": 1.0,
                "volume": 1.0,
                "exchange": "Cross"
            })
            
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
    all_bridges = []
    
    for asset in assets:
        bridges = build_cross_exchange_bridges(asset)
        all_bridges.extend(bridges)

    return all_bridges