import requests
import logging

logger = logging.getLogger(__name__)

class LeaderboardSniper:
    def __init__(self, endpoint="https://gamma-api.polymarket.com/leaderboard"):
        self.endpoint = endpoint

    def fetch_top_traders(self, limit=10, window="30d"):
        """
        Attempts to scrape or pull the PolyMarket Leaderboard.
        Returns a list of wallet addresses if successful.
        """
        try:
            resp = requests.get(self.endpoint, params={"limit": limit, "window": window}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Parse depending on the actual data structure, usually it's a list or data['profiles']
                profiles = data if isinstance(data, list) else data.get("profiles", [])
                
                wallets = []
                for p in profiles:
                    # Collect the wallet address (funder or proxy)
                    addr = p.get("address") or p.get("proxyWallet")
                    if addr:
                        wallets.append(addr)
                        
                logger.info(f"[AUTOPILOT] Sniped {len(wallets)} top traders from the Leaderboard.")
                return wallets
            else:
                logger.warning(f"Failed to fetch leaderboard. Status: {resp.status_code}")
        except Exception as e:
            logger.error(f"Leaderboard fetch error: {e}")
            
        return []
