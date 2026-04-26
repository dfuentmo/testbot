import logging
from core.config import settings

logger = logging.getLogger(__name__)

class Strategy:
    def __init__(self, state_ref):
        self.state = state_ref

    def process_trade_event(self, event):
        """
        Versión simplificada y agresiva. Copia todo lo que sea un trade.
        """
        wallet = event.get("wallet")
        if wallet not in self.state.target_wallets:
            return None

        whale_size = event.get("size", 0.0)
        token_id = event.get("token_id")
        side = event.get("side")

        if whale_size <= 0:
            return None
            
        # Filtro mínimo muy bajo para ver que funciona
        if whale_size < 1.0:
            return None

        # Copia proporcional
        our_size = whale_size * self.state.stake_percentage

        logger.info(f"⚡ [STRATEGY] Copying trade from {wallet}: {side} {token_id} (Our size: ${our_size:.2f})")

        return {
            "token_id": token_id,
            "side": side,
            "size_usd": our_size,
            "whale_size": whale_size,
            "market_slug": event.get("market_slug", "unknown")
        }