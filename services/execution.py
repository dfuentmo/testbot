import logging
import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
from core.config import settings

logger = logging.getLogger(__name__)

class ExecutionEngine:
    def __init__(self, state_ref):
        self.state = state_ref
        self.client = None
        if settings.pk:
            self.client = ClobClient(
                os.getenv("HOST", "https://clob.polymarket.com"),
                key=settings.pk,
                chain_id=settings.chain_id,
                signature_type=settings.signature_type,
                funder=settings.funder if settings.funder else None
            )
            try:
                self.client.set_api_creds(self.client.create_or_derive_api_creds())
                logger.info("ClobClient initialized and authenticated successfully.")
            except Exception as e:
                logger.error(f"Failed to authenticate ClobClient: {e}")
        else:
            logger.warning("No private key found. Execution engine running in unauthenticated mode (read-only).")

    def place_order(self, token_id: str, side: str, size: float, reference_price: float):
        """
        Places a limit order using target's reference price + slippage tolerance. 
        `side` is either "BUY" or "SELL".
        `size` is the dollar amount to spend (if buying) or value to liquidate.
        """
        if side.upper() == "BUY":
            limit_price = reference_price + (reference_price * self.state.slippage_tolerance)
            if limit_price > 0.99: limit_price = 0.99
        else:
            limit_price = reference_price - (reference_price * self.state.slippage_tolerance)
            if limit_price < 0.01: limit_price = 0.01
            
        shares_to_trade = size / reference_price if reference_price > 0 else 0

        if settings.dry_run:
            logger.info(f"[DRY RUN] Would execute: {side} {shares_to_trade:.2f} shares of {token_id} at limit {limit_price:.3f}")
            # Mock successfully placed order
            return {"status": "ok", "price": limit_price, "dry_run": True, "token_id": token_id, "side": side, "size": size}

        if not self.client:
            logger.error("Client not authenticated, cannot place order.")
            return {"status": "error", "message": "Client not authenticated"}

        order_side = BUY if side.upper() == "BUY" else SELL
        
        try:
            oa = OrderArgs(
                price=round(limit_price, 3), 
                size=round(shares_to_trade, 2),
                side=order_side,
                token_id=token_id
            )
            signed_order = self.client.create_order(oa)
            response = self.client.post_order(signed_order)
            logger.info(f"Order executed: {response}")
            return response
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return {"status": "error", "message": str(e)}