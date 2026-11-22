"""Registre comptable unique : seule source de vérité des soldes. Spot, sans levier, sans short."""
import time, uuid
from decimal import Decimal, InvalidOperation

QUOTE = "USDT"
MAX_FAKE_DEPOSIT = Decimal("1000000")

class LedgerError(Exception): pass

def D(x) -> Decimal:
    try: v = Decimal(str(x))
    except InvalidOperation: raise LedgerError(f"nombre invalide: {x}")
    if not v.is_finite(): raise LedgerError("nombre non fini")
    return v

class Ledger:
    def __init__(self, db): self.db = db
    def create_wallet(self, name, simulator="native"):
        if not name or len(name) > 40: raise LedgerError("nom de wallet invalide")
        wid = uuid.uuid4().hex[:12]
        try: self.db.execute("INSERT INTO wallets VALUES(?,?,?,?)", (wid, name, simulator, time.time()))
        except Exception: raise LedgerError(f"wallet '{name}' existe déjà")
        self.db.audit("system", "wallet_create", {"id": wid, "name": name})
        return wid
    def find(self, name_or_id):
        r = self.db.execute("SELECT * FROM wallets WHERE id=? OR name=?", (name_or_id, name_or_id)).fetchone()
        if not r: raise LedgerError(f"wallet introuvable: {name_or_id}")
        return r
    def list_wallets(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM wallets ORDER BY created")]
    def balances(self, wid):
        out = {}
        for r in self.db.execute("SELECT asset, delta FROM ledger WHERE wallet_id=?", (wid,)):
            out[r["asset"]] = out.get(r["asset"], Decimal(0)) + Decimal(r["delta"])
        return {a: q for a, q in out.items() if q != 0}
    def _post(self, wid, asset, delta, kind, idem, ref=None, source="SIMULATED"):
        self.db.execute("INSERT INTO ledger(idem_key,wallet_id,asset,delta,kind,ref,ts,source) VALUES(?,?,?,?,?,?,?,?)",
                        (idem, wid, asset, str(delta), kind, ref, time.time(), source))
    def _seen(self, idem):
        return self.db.execute("SELECT 1 FROM ledger WHERE idem_key LIKE ?", (idem + "%",)).fetchone() is not None
    def deposit(self, wallet, amount, idem=None):
        w = self.find(wallet); amt = D(amount)
        if amt <= 0 or amt > MAX_FAKE_DEPOSIT: raise LedgerError("montant de dépôt fictif invalide")
        idem = idem or uuid.uuid4().hex
        if self._seen(idem + ":dep"): return False
        with self.db.tx(): self._post(w["id"], QUOTE, amt, "deposit_fake", idem + ":dep")
        self.db.audit("system", "deposit_fake", {"wallet": w["id"], "amount": str(amt)})
        return True
    def trade(self, wallet, symbol, side, qty, price, idem, fee_rate=Decimal("0.001"), source="SIMULATED"):
        w = self.find(wallet); q = D(qty); p = D(price)
        if side not in ("buy", "sell"): raise LedgerError("side invalide")
        if q <= 0 or p <= 0: raise LedgerError("quantité/prix invalide")
        base = symbol.split("/")[0]
        if self._seen(idem + ":q"): return False
        notional = q * p; fee = notional * fee_rate
        with self.db.tx():
            bal = self.balances(w["id"])
            if side == "buy":
                need = notional + fee
                if bal.get(QUOTE, Decimal(0)) < need: raise LedgerError("solde insuffisant")
                self._post(w["id"], QUOTE, -need, "buy", idem + ":q", symbol, source)
                self._post(w["id"], base, q, "buy", idem + ":b", symbol, source)
            else:
                if bal.get(base, Decimal(0)) < q: raise LedgerError("position insuffisante")
                self._post(w["id"], base, -q, "sell", idem + ":b", symbol, source)
                self._post(w["id"], QUOTE, notional - fee, "sell", idem + ":q", symbol, source)
        self.db.audit("system", "trade", {"wallet": w["id"], "symbol": symbol, "side": side, "qty": str(q), "price": str(p)})
        return True
    def history(self, wallet, limit=20):
        w = self.find(wallet)
        return [dict(r) for r in self.db.execute("SELECT * FROM ledger WHERE wallet_id=? ORDER BY seq DESC LIMIT ?", (w["id"], limit))]
    def equity(self, wallet, prices):
        w = self.find(wallet); total = Decimal(0)
        for a, q in self.balances(w["id"]).items():
            if a == QUOTE: total += q
            else: total += q * D(prices.get(f"{a}/{QUOTE}", 0))
        return total
