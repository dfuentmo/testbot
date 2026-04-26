import time
import logging
import requests
import json
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

class WalletTracker:
    def __init__(self, state_ref, client=None):
        self.state = state_ref
        self.client = client
        self.running = False
        self.last_trade_hashes = {}

    def _fetch_trades(self, wallet: str):
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
        Loop de alta frecuencia (Estilo OctoBot Fallback).
        """
        logger.info("Starting High-Frequency Polling Tracker (1.0s).")
        self.running = True
        
        while self.running:
            for wallet in self.state.target_wallets:
                trades = self._fetch_trades(wallet)
                if not trades:
                    continue
                
                for trade in trades:
                    if trade.get("type") != "trade":
                        continue
                    
                    trade_hash = trade.get("transactionHash")
                    
                    if self.last_trade_hashes.get(wallet) != trade_hash:
                        if wallet not in self.last_trade_hashes:
                            self.last_trade_hashes[wallet] = trade_hash
                            continue

                        self.last_trade_hashes[wallet] = trade_hash
                        logger.info(f"⚡ NEW TRADE from {wallet}")

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
            
            time.sleep(1.0)
