from abc import ABC, abstractmethod

class ExchangeBase(ABC):
    @abstractmethod
    async def fetch_symbols(self, client):
        pass

    @abstractmethod
    async def fetch_initial_prices(self, client, valid_pairs):
        pass

    @abstractmethod
    async def stream_ws(self, updates_q, symbols):
        pass
