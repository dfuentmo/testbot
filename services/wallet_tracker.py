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
        wallet_clean = wallet.lower().strip()
        url = f"https://data-api.polymarket.com/activity?user={wallet_clean}&limit=5&offset=0&sortBy=TIMESTAMP&sortDirection=DESC"
        try:
            resp = requests.get(url, timeout=10)
            logger.info(f"Checking {wallet_clean}... Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"Data received for {wallet_clean}: {len(data)} items")
                return data
            else:
                logger.error(f"API Error for {wallet_clean}: {resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            logger.error(f"Request Exception for {wallet_clean}: {e}")
        return []

    def stream(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Loop de alta frecuencia (Estilo OctoBot Fallback).
        """
        logger.info(f"Starting High-Frequency Polling Tracker (1.0s) for {len(self.state.target_wallets)} wallets.")
        self.running = True
        
        while self.running:
            if not self.state.target_wallets:
                logger.warning("No target wallets found in state! Waiting...")
                time.sleep(5)
                continue
                
            for wallet in self.state.target_wallets:
                # logger.debug(f"Checking wallet {wallet}...") # Solo si necesitas mucho ruido
                trades = self._fetch_trades(wallet)
                
                if trades:
                    # logger.info(f"Fetched {len(trades)} activities for {wallet}")
                    pass
                
                for trade in trades:
                    t_type = str(trade.get("type", "")).lower()
                    logger.info(f"  Activity found: {t_type}")
                    if t_type != "trade":
                        continue
                    
                    trade_hash = trade.get("transactionHash")
                    
                    if self.last_trade_hashes.get(wallet) != trade_hash:
                        self.last_trade_hashes[wallet] = trade_hash
                        logger.info(f"⚡ DETECTED ACTIVITY from {wallet}")

                        event = {
                            "type": "trade",
                            "wallet": wallet,
                            "market_slug": trade.get("slug", "unknown"),
                            "token_id": trade.get("asset"),
                            "side": str(trade.get("side", "BUY")).upper(),
                            "size": float(trade.get("size", 0)) * float(trade.get("price", 0.5)),
                            "price": float(trade.get("price", 0.5)),
                            "timestamp": time.time(),
                            "hash": trade_hash
                        }
                        logger.info(f">>> TRIGGERING COPY PIPELINE for {wallet}...")
                        callback(event)
            
            time.sleep(1.0)
