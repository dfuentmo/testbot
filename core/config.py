import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load variables from .env file into os.environ
load_dotenv()

class Config(BaseModel):
    # Credentials
    pk: str = os.getenv("PK", "")
    chain_id: int = int(os.getenv("CHAIN_ID", "137"))
    host: str = os.getenv("HOST", "https://clob.polymarket.com")
    funder: str = os.getenv("FUNDER_ADDRESS", "")
    signature_type: int = int(os.getenv("SIGNATURE_TYPE", "0"))

    # Copytrade
    target_wallet: str = os.getenv("TARGET_WALLET", "")
    stake_percentage: float = float(os.getenv("STAKE_PERCENTAGE", "0.01"))
    
    # Risk controls
    max_spend_per_trade: float = float(os.getenv("MAX_SPEND_PER_TRADE", "50.0"))
    min_balance_circuit_breaker: float = float(os.getenv("MIN_BALANCE_CIRCUIT_BREAKER_USDC", "50.0"))
    
    # Flags
    dry_run: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    autopilot_enabled: bool = os.getenv("AUTOPILOT", "false").lower() == "true"
    slippage_tolerance: float = float(os.getenv("SLIPPAGE_TOLERANCE", "0.05"))
    min_trade_size: float = float(os.getenv("MIN_TRADE_SIZE", "10.0"))
    new_only: bool = os.getenv("NEW_ONLY", "true").lower() == "true"

# Global settings instance
settings = Config()

def is_configured() -> bool:
    """Returns True if the essential configuration (private key) is present."""
    return bool(settings.pk)
