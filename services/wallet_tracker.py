import time
import logging
import requests
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

class WalletTracker:
    def __init__(self, state_ref):
        self.state = state_ref
        self.running = False
        self.last_trade_hashes = {} # Evitar duplicados: wallet -> last_hash

    def _fetch_trades(self, wallet: str):
        """
        Consulta los últimos trades de un wallet via Polymarket Data API.
        """
        url = f"https://data-api.polymarket.com/activity?user={wallet}&limit=5&offset=0&sortBy=TIMESTAMP&sortDirection=DESC"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Error fetching trades for {wallet}: {e}")
        return []

    def stream(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Loop de alta frecuencia para detectar trades nuevos.
        """
        logger.info("Starting wallet tracker with High-Frequency Polling.")
        self.running = True
        
        while self.running:
            for wallet in self.state.target_wallets:
                trades = self._fetch_trades(wallet)
                if not trades:
                    continue
                
                # Solo procesamos trades (tipo 'trade')
                for trade in trades:
                    if trade.get("type") != "trade":
                        continue
                    
                    trade_hash = trade.get("transactionHash")
                    
                    # Si es un trade nuevo para este wallet
                    if self.last_trade_hashes.get(wallet) != trade_hash:
                        # Si es la primera vez que vemos este wallet, solo guardamos el hash (no copiamos pasado)
                        if wallet not in self.last_trade_hashes:
                            self.last_trade_hashes[wallet] = trade_hash
                            logger.info(f"Initialized tracking for {wallet}. Last trade: {trade_hash}")
                            continue

                        self.last_trade_hashes[wallet] = trade_hash
                        logger.info(f"⚡ NEW TRADE DETECTED from {wallet}")

                        event = {
                            "type": "trade",
                            "wallet": wallet,
                            "market_slug": trade.get("slug", "unknown"),
                            "token_id": trade.get("asset"),
                            "side": trade.get("side", "BUY").upper(),
                            "size": float(trade.get("size", 0)) * float(trade.get("price", 0)),
                            "price": float(trade.get("price", 0)),
                            "timestamp": time.time(),
                            "hash": trade_hash
                        }
                        callback(event)
            
            # Pausa muy corta para no saturar pero ser rápido (1.5 segundos)
            time.sleep(1.5)
