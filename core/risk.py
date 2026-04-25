import logging
from core.config import settings

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self):
        self.max_spend = settings.max_spend_per_trade
        self.circuit_breaker = settings.min_balance_circuit_breaker
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

        if side in ["BUY", "BUYS"]:
            # 1. Circuit Breaker
            if current_balance < settings.min_balance_circuit_breaker:
                logger.error(f"[RISK] CIRCUIT BREAKER TRIGGERED: Balance {current_balance} < {settings.min_balance_circuit_breaker}. Halting.")
                return None

            # 2. Hard constraint on Max Spend
            if size_usd > self.max_spend:
                logger.warning(f"[RISK] Clipping size ${size_usd:.2f} to max spend ${self.max_spend:.2f}")
                size_usd = self.max_spend
        else:
            # It's a SELL
            # Make sure we own the position
            owned = positions.get(token_id, 0)
            if owned <= 0:
                logger.warning(f"[RISK] Rejected SELL for {token_id} - Position not owned in local portfolio.")
                return None
            
            # Here we could check if we are selling more than we own (size_usd vs value of owned)
            pass

        # 3. Final validation
        if size_usd <= 0:
            return None

        return size_usd

    def update(self, signal):
        side = signal.get("side", "BUY")
        size = signal.get("size_usd", 0.0)
        if side in ["BUY", "BUYS"]:
            self.exposure += size
        else:
            self.exposure = max(0.0, self.exposure - size)