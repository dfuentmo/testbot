import json
import logging
import os
from core.config import settings

logger = logging.getLogger(__name__)

class State:
    def __init__(self, filename="state.json"):
        self.filename = filename
        self.balance = 1000.0
        self.pnl = 0.0
        self.positions = {}
        self.trades = []
        self.signals = []
        self.target_wallets = []
        
        # Dynamic Settings
        self.stake_percentage = settings.stake_percentage
        self.slippage_tolerance = settings.slippage_tolerance
        self.autopilot_enabled = settings.autopilot_enabled
        self.dry_run = settings.dry_run
        self.min_trade_size = settings.min_trade_size
        self.new_only = settings.new_only
        
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.balance = data.get("balance", 1000.0)
                    self.pnl = data.get("pnl", 0.0)
                    self.positions = data.get("positions", {})
                    self.trades = data.get("trades", [])
                    self.target_wallets = data.get("target_wallets", [])
                    
                    # Settings overrides
                    self.stake_percentage = data.get("stake_percentage", self.stake_percentage)
                    self.slippage_tolerance = data.get("slippage_tolerance", self.slippage_tolerance)
                    self.autopilot_enabled = data.get("autopilot_enabled", self.autopilot_enabled)
                    self.dry_run = data.get("dry_run", self.dry_run)
                    self.min_trade_size = data.get("min_trade_size", self.min_trade_size)
                    self.new_only = data.get("new_only", self.new_only)
                logger.info("Local state loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump({
                    "balance": self.balance,
                    "pnl": self.pnl,
                    "positions": self.positions,
                    "trades": self.trades[-100:], # Keep last 100
                    "target_wallets": self.target_wallets,
                    "stake_percentage": self.stake_percentage,
                    "slippage_tolerance": self.slippage_tolerance,
                    "autopilot_enabled": self.autopilot_enabled,
                    "dry_run": self.dry_run,
                    "min_trade_size": self.min_trade_size,
                    "new_only": self.new_only
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def add_trade(self, signal, order_result):
        trade_record = {
            "token_id": signal.get("token_id"),
            "side": signal.get("side"),
            "size_usd": signal.get("size_usd"),
            "status": order_result.get("status"),
            "market": signal.get("market_slug")
        }
        self.trades.append(trade_record)
        self.save()