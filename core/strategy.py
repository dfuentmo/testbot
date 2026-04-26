import logging
from core.config import settings

logger = logging.getLogger(__name__)

class Strategy:
    def __init__(self, state_ref):
        self.stake_percentage = settings.stake_percentage
        self.state = state_ref

    def process_trade_event(self, event):
        """
        Receives a single trade event from the target wallet.
        event: { "wallet", "token_id", "market_slug", "side", "size", "price", ... }
        Calculates our proportional trade.
        """
        wallet = event.get("wallet")
        # Check against the dynamic list
        if wallet not in self.state.target_wallets:
            # We don't care about other wallets
            return None

        whale_size = event.get("size", 0.0)
        token_id = event.get("token_id")
        side = event.get("side")

        if whale_size <= 0:
            return None
            
        # OctoBot Feature: Minimum Trade Size Filter
        if whale_size < self.state.min_trade_size:
            logger.info(f"[STRATEGY] Ignoring trade of ${whale_size:.2f} (below minimum ${self.state.min_trade_size:.2f})")
            return None

        # OctoBot Feature: Price Range Filter
        price = event.get("price", 0.5)
        min_p = getattr(self.state, 'min_price', 0.05)
        max_p = getattr(self.state, 'max_price', 0.95)
        if price < min_p or price > max_p:
            logger.info(f"[STRATEGY] Ignoring trade at price {price} (outside range {min_p}-{max_p})")
            return None

        # OctoBot Feature: New Position Only check
        if self.state.new_only and side == "BUY":
            market_slug = event.get("market_slug")
            if market_slug in self.state.positions:
                 logger.info(f"[STRATEGY] Ignoring BUY for {market_slug} - Position already exists and 'New Only' is active.")
                 return None

        # Calculate our copy size proportionally
        our_size = whale_size * self.state.stake_percentage

        logger.info(f"[STRATEGY] Target wallet deployed ${whale_size:.2f} on {side} for {token_id}. At {self.state.stake_percentage*100}%, we will deploy ${our_size:.2f}")

        return {
            "token_id": token_id,
            "side": side,
            "size_usd": our_size,
            "whale_size": whale_size,
            "market_slug": event.get("market_slug", "unknown")
        }