import requests
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = settings.telegram_token
        self.chat_id = settings.telegram_chat_id
        self.enabled = bool(self.token and self.chat_id)
        logger.info(f"Telegram Service Initializing... Enabled: {self.enabled} (ID: {self.chat_id})")
        if not self.enabled:
            logger.warning(f"Telegram notifications disabled: Token? {bool(self.token)} | Chat ID? {bool(self.chat_id)}")

    def send_message(self, text: str):
        if not self.enabled:
            return
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }, timeout=10)
            logger.info(f"Telegram Post Status: {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"Failed to send Telegram message. Response: {resp.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    def notify_trade(self, wallet, side, market, size, status):
        emoji = "🚀" if status in ["ok", "success"] else "⚠️"
        msg = (
            f"{emoji} <b>Polymarket Copytrade</b>\n\n"
            f"<b>Wallet:</b> <code>{wallet[:10]}...</code>\n"
            f"<b>Action:</b> {side}\n"
            f"<b>Market:</b> {market}\n"
            f"<b>Size:</b> ${size:.2f}\n"
            f"<b>Status:</b> {status}"
        )
        self.send_message(msg)

    def notify_error(self, error_msg: str):
        msg = f"❌ <b>CRITICAL ERROR</b>\n\n{error_msg}"
        self.send_message(msg)
