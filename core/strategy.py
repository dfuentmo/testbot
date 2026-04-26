import logging
import time
from core.config import settings

logger = logging.getLogger(__name__)

class Strategy:
    def __init__(self, state_ref):
        self.state = state_ref

    def process_trade_event(self, event):
        """
        Copia trades de ballenas con filtros de riesgo y temporalidad.
        Para mercados de clima (hondacivic), ignora trades viejos (>5 min) 
        para evitar precios "viciados" con liquidez desaparecida.
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

        # Validación temporal: rechazar trades muy viejos (>5 minutos)
        # Importante para mercados diarios de clima donde la liquidez se evapora
        event_timestamp = event.get("timestamp", time.time())
        current_time = time.time()
        trade_age_seconds = current_time - event_timestamp
        
        if trade_age_seconds > 300:  # 5 minutos = 300 segundos
            logger.warning(f"[STRATEGY] Rejecting stale trade - age: {trade_age_seconds:.0f}s > 300s (liquidity likely gone)")
            return None

        # Copia proporcional
        our_size = whale_size * self.state.stake_percentage

        logger.info(f"⚡ [STRATEGY] Copying trade from {wallet}: {side} {token_id} (Our size: ${our_size:.2f}, trade age: {trade_age_seconds:.0f}s)")

        return {
            "token_id": token_id,
            "side": side,
            "size_usd": our_size,
            "whale_size": whale_size,
            "price": event.get("price", 0.5),
            "market_slug": event.get("market_slug", "unknown")
        }