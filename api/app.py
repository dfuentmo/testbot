import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.config import settings
import logging

# We import the instances from bot main instead of re-instantiating them
# so we can share memory of what the bot is actually doing
from bot.main import state, portfolio, tracker, start_bot_loop

app = FastAPI(title="Polymarket CopyTrade Bot Dashboard")

# Strategy presets - define different strategies with predefined settings
STRATEGY_PRESETS = {
    "hondacivic": {
        "stake_percentage": 0.002,  # 0.2% stake (con $1500 entrada promedio = ~$3 nuestro)
        "slippage_tolerance": 0.01,  # 1% slippage INTRANSIGENTE para clima volátil
        "autopilot_enabled": False,
        "dry_run": True,
        "min_trade_size": 1.0,  # Rechazar trades < $1 USDC
        "new_only": True,
        "min_price": 0.15,  # Evitar apuestas "basura" - protege capital
        "max_price": 0.80,  # "Recoger monedas frente a apisonadora" riesgo muy alto arriba de 0.80
        "min_balance_circuit_breaker": 5.0,  # Parar si balance < $5
        "max_spend_per_trade": 5.0,  # MÁXIMO $5 por operación
        "max_open_positions": 8  # Máximo 8 posiciones simultáneas para evitar bloqueo
    },
    "conservative": {
        "stake_percentage": 0.01,  # 1% stake
        "slippage_tolerance": 0.05,  # 5% slippage
        "autopilot_enabled": False,
        "dry_run": True,
        "min_trade_size": 50.0,
        "new_only": True,
        "min_price": 0.1,
        "max_price": 0.9,
        "min_balance_circuit_breaker": 50.0,
        "max_spend_per_trade": 50.0,
        "max_open_positions": 5
    },
    "aggressive": {
        "stake_percentage": 0.10,  # 10% stake
        "slippage_tolerance": 0.02,  # 2% slippage
        "autopilot_enabled": True,
        "dry_run": False,
        "min_trade_size": 1.0,
        "new_only": False,
        "min_price": 0.01,
        "max_price": 0.99,
        "min_balance_circuit_breaker": 5.0,
        "max_spend_per_trade": 200.0,
        "max_open_positions": 15
    }
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start bot in background when running the API
@app.on_event("startup")
def startup_event():
    logging.info("Starting background bot thread...")
    bot_thread = threading.Thread(target=start_bot_loop, daemon=True)
    bot_thread.start()

@app.get("/status")
def status():
    return {
        "balance": state.balance,
        "pnl": state.pnl,
        "positions": state.positions,
        "recent_trades": state.trades[-10:], # Return last 10 trades
        "balance_history": state.balance_history,
        "deposits": state.deposits,
        "target_wallets": state.target_wallets,
        "stake_percentage": state.stake_percentage,
        "slippage_tolerance": state.slippage_tolerance,
        "autopilot_enabled": state.autopilot_enabled,
        "dry_run": state.dry_run,
        "min_trade_size": state.min_trade_size,
        "new_only": state.new_only,
        "min_price": state.min_price,
        "max_price": state.max_price,
        "min_balance_circuit_breaker": state.min_balance_circuit_breaker,
        "max_spend_per_trade": state.max_spend_per_trade
    }

class DepositRequest(BaseModel):
    amount: float

@app.post("/deposit")
def make_deposit(req: DepositRequest):
    if req.amount > 0:
        state.deposit(req.amount)
        return {"status": "ok", "new_balance": state.balance}
    return {"status": "error", "message": "Amount must be positive"}

class SettingsUpdate(BaseModel):
    stake_percentage: float = None
    slippage_tolerance: float = None
    autopilot_enabled: bool = None
    dry_run: bool = None
    min_trade_size: float = None
    new_only: bool = None
    min_price: float = None
    max_price: float = None
    min_balance_circuit_breaker: float = None
    max_spend_per_trade: float = None

@app.post("/settings")
def update_settings(updates: SettingsUpdate):
    if updates.stake_percentage is not None:
        state.stake_percentage = updates.stake_percentage
    if updates.slippage_tolerance is not None:
        state.slippage_tolerance = updates.slippage_tolerance
    if updates.autopilot_enabled is not None:
        state.autopilot_enabled = updates.autopilot_enabled
    if updates.dry_run is not None:
        state.dry_run = updates.dry_run
    if updates.min_trade_size is not None:
        state.min_trade_size = updates.min_trade_size
    if updates.new_only is not None:
        state.new_only = updates.new_only
    if updates.min_price is not None:
        state.min_price = updates.min_price
    if updates.max_price is not None:
        state.max_price = updates.max_price
    if updates.min_balance_circuit_breaker is not None:
        state.min_balance_circuit_breaker = updates.min_balance_circuit_breaker
    if updates.max_spend_per_trade is not None:
        state.max_spend_per_trade = updates.max_spend_per_trade
    
    state.save()
    return {"status": "ok"}

@app.post("/wallets/{address}")
def add_wallet(address: str):
    if address not in state.target_wallets:
        state.target_wallets.append(address)
        state.save()
    return {"status": "ok", "wallets": state.target_wallets}

@app.delete("/wallets/{address}")
def remove_wallet(address: str):
    if address in state.target_wallets:
        state.target_wallets.remove(address)
        state.save()
    return {"status": "ok", "wallets": state.target_wallets}

@app.post("/reset")
def reset_state(req: DepositRequest = None):
    initial_amount = req.amount if req and req.amount > 0 else 50.0
    state.reset(initial_amount)
    
    # Synchronize portfolio
    portfolio.balance = initial_amount
    portfolio.positions = {}
    
    return {"status": "ok", "message": f"System reset to ${initial_amount}"}

@app.post("/strategy/apply/{strategy_name}")
def apply_strategy(strategy_name: str):
    """Apply a predefined strategy preset to the current state."""
    strategy_name_lower = strategy_name.lower()
    
    if strategy_name_lower not in STRATEGY_PRESETS:
        return {
            "status": "error",
            "message": f"Strategy '{strategy_name}' not found. Available: {list(STRATEGY_PRESETS.keys())}"
        }
    
    strategy = STRATEGY_PRESETS[strategy_name_lower]
    
    # Apply all settings from the strategy preset
    state.stake_percentage = strategy["stake_percentage"]
    state.slippage_tolerance = strategy["slippage_tolerance"]
    state.autopilot_enabled = strategy["autopilot_enabled"]
    state.dry_run = strategy["dry_run"]
    state.min_trade_size = strategy["min_trade_size"]
    state.new_only = strategy["new_only"]
    state.min_price = strategy["min_price"]
    state.max_price = strategy["max_price"]
    state.min_balance_circuit_breaker = strategy["min_balance_circuit_breaker"]
    state.max_spend_per_trade = strategy["max_spend_per_trade"]
    
    # Apply max_open_positions if defined in strategy
    if "max_open_positions" in strategy:
        state.max_open_positions = strategy["max_open_positions"]
    
    # Save the new configuration to state.json
    state.save()
    
    return {
        "status": "ok",
        "message": f"Strategy '{strategy_name}' applied successfully",
        "strategy": strategy
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("api/templates/dashboard.html", "r") as f:
        html = f.read()
    return html