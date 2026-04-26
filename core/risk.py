import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, state_ref):
        self.state = state_ref
        self.exposure = 0.0

    def check(self, signal, current_balance, positions=None):
        """
        Validates whether to proceed with the trade.
        signal includes: "token_id", "side", "size_usd"
        Returns the confirmed size to trade, or None if rejected.
        """
        if positions is None:
            positions = {}
            
        size_usd = signal.get("size_usd", 0.0)
        side = signal.get("side", "BUY")
        token_id = signal.get("token_id")
        price = signal.get("price", 0.5)

        # 0. Price Range validation
        if side in ["BUY", "BUYS"]:
            if price < self.state.min_price or price > self.state.max_price:
                logger.warning(f"[RISK] Rejected trade - Price {price:.2f} outside bounds ({self.state.min_price}-{self.state.max_price})")
                return None

        if side in ["BUY", "BUYS"]:
            # 1. Circuit Breaker (using dynamic state)
            limit = self.state.min_balance_circuit_breaker
            if current_balance < limit:
                logger.error(f"[RISK] CIRCUIT BREAKER TRIGGERED: Balance {current_balance:.2f} < {limit:.2f}. Halting.")
                return None

            # 2. Hard constraint on Max Spend (using dynamic state)
            max_spend = self.state.max_spend_per_trade
            if size_usd > max_spend:
                logger.warning(f"[RISK] Clipping size ${size_usd:.2f} to max spend ${max_spend:.2f}")
                size_usd = max_spend
        else:
            # It's a SELL
            # Make sure we own the position
            owned = positions.get(token_id, 0)
            if owned <= 0:
                logger.warning(f"[RISK] Rejected SELL for {token_id} - Position not owned in local portfolio.")
                return None
            
        # 3. Min Trade Size validation
        min_size = self.state.min_trade_size
        if size_usd < min_size:
            logger.warning(f"[RISK] Rejected trade - Size ${size_usd:.2f} is below minimum ${min_size:.2f}")
            return None

        return size_usd

    def update(self, signal):
        side = signal.get("side", "BUY")
        size = signal.get("size_usd", 0.0)
        if side in ["BUY", "BUYS"]:
            self.exposure += size
        else:
            self.exposure = max(0.0, self.exposure - size)