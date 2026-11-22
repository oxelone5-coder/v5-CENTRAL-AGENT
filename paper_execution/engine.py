"""Moteur d'exécution PAPER : n'exécute que ce que le Risk Manager autorise."""
import uuid, time
from decimal import Decimal
from wallets.ledger import LedgerError

class PaperExecutionEngine:
    def __init__(self, db, ledger, risk, provider):
        self.db, self.ledger, self.risk, self.provider = db, ledger, risk, provider
    def prices(self):
        return {s: self.provider.last_price(s) for s in ("BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT")}
    def submit(self, wallet, symbol, side, qty, idem=None, actor="human"):
        idem = idem or uuid.uuid4().hex
        row = self.db.execute("SELECT status FROM orders WHERE idem_key=?", (idem,)).fetchone()
        if row: return {"status": row["status"], "duplicate": True}
        prices = self.prices(); price = Decimal(str(prices[symbol]))
        oid = uuid.uuid4().hex[:12]
        dec = self.risk.check(wallet, symbol, side, qty, price, prices)
        if not dec.allowed:
            self._rec(oid, idem, wallet, symbol, side, qty, price, "REJECTED", dec.reason)
            return {"status": "REJECTED", "reason": dec.reason, "order_id": oid}
        try:
            self.ledger.trade(wallet, symbol, side, qty, price, idem, source=getattr(self.provider, "source", "SIMULATED"))
            self._rec(oid, idem, wallet, symbol, side, qty, price, "FILLED", "")
            return {"status": "FILLED", "price": str(price), "order_id": oid, "data_source": self.provider.source}
        except LedgerError as e:
            self._rec(oid, idem, wallet, symbol, side, qty, price, "REJECTED", str(e))
            return {"status": "REJECTED", "reason": str(e), "order_id": oid}
        except Exception as e:
            self._rec(oid, idem, wallet, symbol, side, qty, price, "UNKNOWN", str(e))
            from risk.safety import State
            self.risk.safety.escalate(State.ENTRY_LOCK, "ordre UNKNOWN")
            return {"status": "UNKNOWN", "reason": str(e), "order_id": oid}
    def _rec(self, oid, idem, wallet, sym, side, qty, price, status, reason):
        self.db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (oid, idem, wallet, sym, side, str(qty), str(price), status, reason, time.time()))
        self.db.audit("paper_engine", "order", {"id": oid, "status": status, "reason": reason})
