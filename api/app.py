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
        "target_wallets": state.target_wallets,
        "stake_percentage": state.stake_percentage,
        "slippage_tolerance": state.slippage_tolerance,
        "autopilot_enabled": state.autopilot_enabled,
        "dry_run": state.dry_run,
        "min_trade_size": state.min_trade_size,
        "new_only": state.new_only,
        "min_price": state.min_price,
        "max_price": state.max_price
    }

class SettingsUpdate(BaseModel):
    stake_percentage: float = None
    slippage_tolerance: float = None
    autopilot_enabled: bool = None
    dry_run: bool = None
    min_trade_size: float = None
    new_only: bool = None
    min_price: float = None
    max_price: float = None

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

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("api/templates/dashboard.html", "r") as f:
        html = f.read()
    return html