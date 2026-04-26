import logging
import threading
from core.strategy import Strategy
from core.risk import RiskManager
from services.execution import ExecutionEngine
from engine.portfolio import Portfolio
from services.wallet_tracker import WalletTracker
from services.leaderboard import LeaderboardSniper
from services.market_resolver import MarketResolver
from services.notifier import TelegramNotifier
from core.state import State
from core.config import settings
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global instances (also used by the API)
state = State()
strategy = Strategy(state)
risk = RiskManager(state)
exec_engine = ExecutionEngine(state)
portfolio = Portfolio()
tracker = WalletTracker(state, client=exec_engine.client)
notifier = TelegramNotifier()
# [TEMPORAL: RESOLUCIÓN MANUAL]
resolver = MarketResolver(state, portfolio, exec_engine)

def handle_trade_event(event):
    """
    Main pipeline to process an incoming trade from a tracked wallet.
    """
    logger.info(f"Incoming event from {event.get('wallet')}: {event}")
    
    # 1. Strategy: convert whale trade to our signal
    signal = strategy.process_trade_event(event)

    if not signal:
        logger.info("Signal discarded or sizing resulted in 0.")
        return

    # 2. Risk: ensure the signal is safe to execute based on limits and balance
    # Synchronize portfolio balance with global state balance
    portfolio.balance = state.balance
    current_balance = state.balance
    safe_size = risk.check(signal, current_balance, portfolio.positions)

    if not safe_size:
        logger.warning("Trade rejected by Risk Manager.")
        notifier.notify_error(f"Trade rejected by Risk Manager for {event.get('wallet')}. Balance: ${state.balance:.2f}")
        return
    
    signal["size_usd"] = safe_size

    # 3. Execution: Send order to Polymarket
    reference_price = event.get("price", 0.5)
    logger.info(f"Executing Trade: {signal['side']} {signal['token_id']} for ${safe_size:.2f} (Target Price: {reference_price})")
    result = exec_engine.place_order(signal["token_id"], signal["side"], safe_size, reference_price)
    
    if result.get("status") == "error":
        logger.error(f"Execution failed: {result}")
    else:
        # 4. State Management: update local portfolio and history
        price = result.get("price", 0.5) # Fallback price if not resolved immediately
        portfolio.apply(signal["token_id"], signal["side"], safe_size, price)
        state.update_balance(portfolio.balance)
        state.positions = portfolio.positions
        
        # Notify success
        notifier.notify_trade(
            event.get("wallet"), 
            signal["side"], 
            signal["market_slug"], 
            safe_size, 
            result.get("status", "ok")
        )

    # Ensure we log the trade attempt whether successful or not
    state.add_trade(signal, result)
    risk.update(signal)

    logger.info(f"STATE UPDATED: Balance = ${state.balance:.2f}")

def leaderboard_loop():
    sniper = LeaderboardSniper()
    while True:
        if settings.autopilot_enabled:
            logger.info("Autopilot enabled. Firing Leaderboard Sniper...")
            wallets = sniper.fetch_top_traders()
            if wallets:
                new_added = False
                for w in wallets:
                    if w not in state.target_wallets:
                        state.target_wallets.append(w)
                        new_added = True
                if new_added:
                    state.save()
                    logger.info("State updated with new Top Leaderboard Wallets.")
        time.sleep(3600) # every hour

def start_bot_loop():
    # Start the market resolver in a background thread
    resolver_thread = threading.Thread(target=resolver.run_loop, daemon=True)
    resolver_thread.start()
    logger.info("Market Resolver background thread started.")

    # Run tracker in the main thread (it's a blocking loop)
    tracker.stream(handle_trade_event)

if __name__ == "__main__":
    # Notify Telegram about startup (only from the bot container)
    notifier.send_message("🤖 <b>Polymarket CopyTrade Bot Online</b>\nEl sistema de vigilancia de ballenas está activo.")
    start_bot_loop()