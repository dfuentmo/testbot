class WalletRanker:
    def __init__(self):
        self.scores = {}

    def score(self, wallet):
        return self.scores.get(wallet, 1)

    def update(self, wallet, pnl):
        self.scores[wallet] = self.score(wallet) + pnl * 0.1