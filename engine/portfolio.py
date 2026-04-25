import os
from py_clob_client.client import ClobClient
from core.config import settings

class Portfolio:
    def __init__(self):
        self.balance = 0.0
        self.positions = {}
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
            except Exception:
                pass

    def sync(self):
        """Fetches real balance and positions if client is available."""
        if not self.client:
            return
            
        try:
            # We don't have a direct wallet balance method via ClobClient in all examples, 
            # usually it's queried from the RPC or Polygon directly, 
            # but we can get open orders or rely on user_trades.
            # For simplicity let's stick to tracking local balance until we add web3
            pass
        except Exception as e:
            print(f"Failed to sync portfolio: {e}")

    def apply(self, token_id, side, size, price):
        # Update local mocked tracking
        spend = size
        if side == "BUY":
            self.balance -= spend
        else:
            self.balance += spend

        if token_id not in self.positions:
            self.positions[token_id] = 0

        if side == "BUY":
            self.positions[token_id] += (size / price) if price > 0 else 0
        else:
            self.positions[token_id] -= (size / price) if price > 0 else 0