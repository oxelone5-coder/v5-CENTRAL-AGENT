"""Risk Manager : indépendant des agents. Fail closed."""
from dataclasses import dataclass
from decimal import Decimal
from risk.safety import SafetyController

LIMITS = {"max_position_pct": Decimal("0.40"), "max_order_pct": Decimal("0.25"), "max_drawdown_pct": Decimal("0.30")}

@dataclass
class Decision:
    allowed: bool
    reason: str

class RiskManager:
    def __init__(self, ledger, safety: SafetyController):
        self.ledger, self.safety = ledger, safety
    def check(self, wallet, symbol, side, qty, price, prices) -> Decision:
        try:
            if not self.safety.allows(side):
                return Decision(False, f"état {self.safety.state.name} : {side} interdit")
            q, p = Decimal(str(qty)), Decimal(str(price))
            if q <= 0 or p <= 0: return Decision(False, "paramètres invalides")
            eq = self.ledger.equity(wallet, prices)
            if side == "buy":
                if eq <= 0: return Decision(False, "equity nulle")
                if q * p > eq * LIMITS["max_order_pct"]: return Decision(False, "ordre > limite")
                base = symbol.split("/")[0]
                w = self.ledger.find(wallet)
                pos = self.ledger.balances(w["id"]).get(base, Decimal(0)) * p
                if (pos + q * p) > eq * LIMITS["max_position_pct"]: return Decision(False, "concentration > limite")
            return Decision(True, "ok")
        except Exception as e:
            return Decision(False, f"erreur risk manager: {e}")
