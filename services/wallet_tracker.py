import json
import asyncio
import logging
import time
import websockets
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

class WalletTracker:
    def __init__(self, state_ref):
        self.state = state_ref
        self.ws_url = "wss://gamma-api.polymarket.com/ws"
        self.running = False

    async def _listen(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Connects to Polymarket WS and listens for trades from target wallets.
        """
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    logger.info(f"Connected to Polymarket WebSocket: {self.ws_url}")
                    
                    # Subscribe to all trade events
                    # Note: Ideally we filter by user at the WS level if supported, 
                    # but usually we subscribe to a topic and filter locally for speed.
                    subscribe_msg = {
                        "type": "subscribe",
                        "topic": "trades"
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    async for message in websocket:
                        data = json.loads(message)
                        # The format varies, but usually it's a list or a single event
                        # We look for trades involving our target_wallets
                        await self._process_ws_message(data, callback)
                        
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

    async def _process_ws_message(self, data, callback):
        """
        Parses the WS message and filters by our target wallets.
        """
        # Polymarket WS structure for trades (simplified example)
        # { "topic": "trades", "payload": { "proxy": "0x...", "size": "...", "price": "...", "asset": "..." } }
        if data.get("topic") == "trades":
            payload = data.get("payload", {})
            user_wallet = payload.get("proxy") # Polymarket uses proxy wallets for trades
            
            if user_wallet in self.state.target_wallets:
                logger.info(f"⚡ REAL-TIME TRADE DETECTED from {user_wallet}")
                
                event = {
                    "type": "trade",
                    "wallet": user_wallet,
                    "market_slug": payload.get("slug", "unknown"),
                    "token_id": payload.get("asset"),
                    "side": payload.get("side", "BUY").upper(),
                    "size": float(payload.get("size", 0)) * float(payload.get("price", 0)), # USDC size
                    "price": float(payload.get("price", 0)),
                    "timestamp": time.time(),
                    "hash": payload.get("transactionHash")
                }
                callback(event)

    def stream(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Starts the asynchronous websocket listener.
        """
        logger.info("Starting wallet tracker with WebSockets (Real-time).")
        self.running = True
        # Run the async loop in the current thread (which is a daemon thread in bot/main.py)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._listen(callback))
