import requests
import time
import logging
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

class WalletTracker:
    def __init__(self, state_ref):
        self.state = state_ref
        self.endpoint = "https://data-api.polymarket.com/activity"
        self.last_timestamps = {}

    
    def fetch_latest_trades(self, user_address: str):
        """
        Polls the Polymarket Data API for the latest trades of a specific user.
        Uses `last_timestamps` to ensure we don't return duplicate events.
        """
        try:
            resp = requests.get(self.endpoint, params={
                "user": user_address,
                "limit": "10",
                "offset": "0",
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC",
            }, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                new_trades = []
                
                last_seen_ts = self.last_timestamps.get(user_address, 0)
                max_ts_in_batch = last_seen_ts
                
                # Data is sorted DESC, so iterate reversed if we want timeline order, 
                # but we just need to filter by timestamp.
                for activity in data:
                    ts = float(activity.get("timestamp", 0))
                    # Only process new trades
                    if ts > last_seen_ts:
                        # Sometimes type is "Trade" or generic
                        t_type = activity.get("type", "").upper()
                        if t_type in ["TRADE", "BUYS", "BUY", "SELL"]:
                            new_trades.append({
                                "type": "trade",
                                "wallet": user_address,
                                "market_slug": activity.get("slug"),
                                "token_id": activity.get("asset"), # Data API usually exposes asset ID as the condition/token id
                                "side": activity.get("side", "BUY"), # YES/NO or BUY/SELL
                                "size": float(activity.get("usdcSize", 0)),
                                "price": float(activity.get("price", 0)),
                                "timestamp": ts,
                                "hash": activity.get("transactionHash")
                            })
                        if ts > max_ts_in_batch:
                            max_ts_in_batch = ts
                            
                if max_ts_in_batch > last_seen_ts:
                    self.last_timestamps[user_address] = max_ts_in_batch
                    
                # New trades will be emitted in ascending order (oldest first)
                return sorted(new_trades, key=lambda x: x["timestamp"])
                
        except Exception as e:
            logger.error(f"Error fetching from data-api for {user_address}: {e}")
            
        return []

    def stream(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Polls the API for the target wallet's trades and invokes the callback for new ones.
        """
        logger.info("Starting wallet tracker with dynamic polling.")
        while True:
            try:
                if self.state.target_wallets:
                    for wallet in self.state.target_wallets:
                        trades = self.fetch_latest_trades(wallet)
                        for trade in trades:
                            logger.info(f"Detected new trade from {wallet}")
                            callback(trade)
            except Exception as e:
                logger.error(f"Error fetching trades: {e}")
            
            time.sleep(5)  # Poll every 5 seconds
