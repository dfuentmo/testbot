import json
import logging
import os
import time
from core.config import settings

logger = logging.getLogger(__name__)

class State:
    def __init__(self, filename="state.json"):
        self.filename = filename
        self.balance = 1000.0
        self.pnl = 0.0
        self.positions = {}
        self.trades = []
        self.balance_history = []
        self.deposits = []
        self.target_wallets = []
        
        # Dynamic Settings
        self.stake_percentage = settings.stake_percentage
        self.slippage_tolerance = settings.slippage_tolerance
        self.autopilot_enabled = settings.autopilot_enabled
        self.dry_run = settings.dry_run
        self.min_trade_size = settings.min_trade_size
        self.new_only = settings.new_only
        self.min_price = 0.05
        self.max_price = 0.95
        self.min_balance_circuit_breaker = settings.min_balance_circuit_breaker
        self.max_spend_per_trade = settings.max_spend_per_trade
        self.max_open_positions = 10  # Default limit
        
        self.load()
        
        if not self.balance_history:
            self.record_balance()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.balance = data.get("balance", 1000.0)
                    self.pnl = data.get("pnl", 0.0)
                    self.positions = data.get("positions", {})
                    self.trades = data.get("trades", [])
                    self.balance_history = data.get("balance_history", [])
                    self.deposits = data.get("deposits", [])
                    self.target_wallets = data.get("target_wallets", [])
                    
                    # Settings overrides
                    self.stake_percentage = data.get("stake_percentage", self.stake_percentage)
                    self.slippage_tolerance = data.get("slippage_tolerance", self.slippage_tolerance)
                    self.autopilot_enabled = data.get("autopilot_enabled", self.autopilot_enabled)
                    self.dry_run = data.get("dry_run", self.dry_run)
                    self.min_trade_size = data.get("min_trade_size", self.min_trade_size)
                    self.new_only = data.get("new_only", self.new_only)
                    self.min_price = data.get("min_price", 0.05)
                    self.max_price = data.get("max_price", 0.95)
                    self.min_balance_circuit_breaker = data.get("min_balance_circuit_breaker", self.min_balance_circuit_breaker)
                    self.max_spend_per_trade = data.get("max_spend_per_trade", self.max_spend_per_trade)
                    self.max_open_positions = data.get("max_open_positions", 10)
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
                    "trades": self.trades[-1000:], # Keep last 1000
                    "balance_history": self.balance_history[-500:], 
                    "deposits": self.deposits[-100:], # Keep last 100 deposits
                    "target_wallets": self.target_wallets,
                    "stake_percentage": self.stake_percentage,
                    "slippage_tolerance": self.slippage_tolerance,
                    "autopilot_enabled": self.autopilot_enabled,
                    "dry_run": self.dry_run,
                    "min_trade_size": self.min_trade_size,
                    "new_only": self.new_only,
                    "min_price": self.min_price,
                    "max_price": self.max_price,
                    "min_balance_circuit_breaker": self.min_balance_circuit_breaker,
                    "max_spend_per_trade": self.max_spend_per_trade,
                    "max_open_positions": self.max_open_positions
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def record_balance(self):
        self.balance_history.append({
            "timestamp": int(time.time()),
            "balance": round(self.balance, 2)
        })
        if len(self.balance_history) > 200:
            self.balance_history = self.balance_history[-200:]

    def add_trade(self, signal, order_result):
        trade_record = {
            "token_id": signal.get("token_id"),
            "side": signal.get("side"),
            "size_usd": signal.get("size_usd"),
            "status": order_result.get("status"),
            "market": signal.get("market_slug"),
            "timestamp": int(time.time())
        }
        self.trades.append(trade_record)
        self.record_balance()
        self.save()

    def deposit(self, amount):
        """Adds funds to the dummy balance and records it."""
        self.balance += amount
        self.deposits.append({
            "timestamp": int(time.time()),
            "amount": amount
        })
        self.record_balance()
        self.save()
        logger.info(f"Deposit of ${amount:.2f} recorded. New balance: ${self.balance:.2f}")

    def settle_position(self, token_id, final_price, market_name):
        if token_id in self.positions:
            shares = self.positions[token_id]
            payout = shares * final_price
            self.balance += payout
            self.trades.append({
                "token_id": token_id,
                "side": "SETTLE",
                "size_usd": payout,
                "status": "success",
                "market": market_name,
                "timestamp": int(time.time())
            })
            del self.positions[token_id]
            logger.info(f"Settled position {token_id} ({market_name}). Payout: ${payout:.2f}")
            self.record_balance()
            self.save()
            
    def update_balance(self, new_balance):
        if abs(self.balance - new_balance) > 0.01:
            self.balance = new_balance
            self.record_balance()
            self.save()

    def reset(self, initial_balance=1000.0):
        """Resets the state to a clean slate."""
        self.balance = initial_balance
        self.pnl = 0.0
        self.positions = {}
        self.trades = []
        self.balance_history = []
        self.deposits = []
        self.record_balance()
        self.save()
        logger.info(f"State reset to {initial_balance}.")