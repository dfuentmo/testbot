import logging
import time
import requests
from core.state import State
from engine.portfolio import Portfolio

logger = logging.getLogger(__name__)

class MarketResolver:
    """
    Service to monitor open positions and settle them when the market resolves.
    """
    def __init__(self, state: State, portfolio: Portfolio, execution_engine):
        self.state = state
        self.portfolio = portfolio
        self.execution_engine = execution_engine

    def check_resolutions(self):
        """
        Iterates through open positions and checks if they have resolved on Polymarket.
        """
        if not self.state.positions:
            return

        logger.info(f"Checking resolutions for {len(self.state.positions)} open positions...")
        
        # Work on a copy of keys
        token_ids = list(self.state.positions.keys())
        
        for token_id in token_ids:
            try:
                # Use the Data API to get market status for the token
                # The endpoint https://clob.polymarket.com/markets/<token_id> returns market details
                url = f"https://clob.polymarket.com/markets/{token_id}"
                resp = requests.get(url, timeout=10)
                
                if resp.status_code != 200:
                    logger.warning(f"Could not fetch market info for {token_id}: {resp.status_code}")
                    continue
                    
                market_data = resp.json()
                
                # Check if the market is closed/resolved
                # Polymarket CLOB API marks resolved markets with price 1 or 0 or 'closed': true
                
                # Let's check the orderbook price as a proxy for resolution
                # If the market is resolved, the price will be exactly 1.0 or 0.0
                
                # We can also check if the market is 'active'
                if not market_data.get("active", True):
                    logger.info(f"Market for {token_id} is inactive. Checking resolution...")
                    
                # Robust check: Get current price
                # If we are in dry run or real mode, we can use the execution engine client
                price = 0.5
                if self.execution_engine and self.execution_engine.client:
                    try:
                        # Get mid price or last trade price
                        price_resp = self.execution_engine.client.get_midpoint(token_id)
                        price = float(price_resp.get("mid", 0.5))
                    except:
                        # Fallback: check if it's resolved via Data API directly if possible
                        pass

                # If price is at extremes, it's likely resolved
                if price >= 0.995:
                    logger.info(f"🏆 Position {token_id} WON! (Price: {price})")
                    self.state.settle_position(token_id, 1.0, market_data.get("description", "Unknown"))
                elif price <= 0.005:
                    logger.info(f"💀 Position {token_id} LOST. (Price: {price})")
                    self.state.settle_position(token_id, 0.0, market_data.get("description", "Unknown"))
                else:
                    logger.debug(f"Position {token_id} still active at {price}")

            except Exception as e:
                logger.error(f"Error resolving {token_id}: {e}")

    def run_loop(self):
        logger.info("Market Resolver loop started.")
        while True:
            try:
                self.check_resolutions()
            except Exception as e:
                logger.error(f"Error in resolver loop: {e}")
            time.sleep(300) # Check every 5 minutes
