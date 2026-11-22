"""Logique métier des commandes (pure, testable sans Discord)."""
import time
from decimal import Decimal
from risk.manager import LIMITS
from wallets.ledger import QUOTE
from orchestration.orchestrator import format_report
from strategies.sma_breakout import backtest
from market_data.provider import SYMBOLS, SyntheticProvider

HELP = """**/v5 help** — commandes
status · market · portfolio · analyze · pause · resume · emergency_halt
🔒 Owner uniquement : pause, resume, emergency_halt"""


class Services:
    def __init__(self, settings, db, ledger, engine, safety, orchestrator, provider):
        self.s, self.db, self.ledger, self.engine, self.safety, self.orch, self.provider = settings, db, ledger, engine, safety, orchestrator, provider

    def is_owner(self, uid): return uid == self.s.owner_id

    def status(self):
        return (f"État: **{self.safety.state.name}** | source marché: **{self.provider.source}** | "
                f"wallets: {len(self.ledger.list_wallets())} | mode: PAPER uniquement")

    def market(self):
        L = [f"**Marché** (source: {self.provider.source})"]
        for s in SYMBOLS:
            cs = self.provider.candles(s, 50); c0, c1 = cs[0].c, cs[-1].c
            L.append(f"{s}: {c1:.4f} ({(c1/c0-1):+.2%} /50 bougies)")
        return "\n".join(L)

    def _own(self, uid):
        if not self.is_owner(uid):
            raise PermissionError("Owner only")

    def pause(self, uid):
        self._own(uid); self.safety.set_state(__import__("risk.safety", fromlist=["State"]).State.HALT); return "Système en pause"

    def resume(self, uid):
        self._own(uid); self.safety.unlock(__import__("risk.safety", fromlist=["State"]).State.NORMAL, uid, self.s.owner_id); return "Système repris"

    def emergency_halt(self, uid):
        self._own(uid); self.safety.escalate(__import__("risk.safety", fromlist=["State"]).State.HALT, "emergency"); return "EMERGENCY HALT activé"

    async def analyze(self, trigger="manual"):
        return format_report(await self.orch.run_analysis(trigger))

    BOT_WALLET_NAME = "V5-Bot-Wallet"

    def ensure_bot_wallet(self, capital: float = 10000.0):
        try:
            self.ledger.find(self.BOT_WALLET_NAME)
        except Exception:
            self.ledger.create_wallet(self.BOT_WALLET_NAME)
            self.ledger.deposit(self.BOT_WALLET_NAME, str(capital))
            self.db.audit("system", "bot_wallet_created", {"capital": capital})

    def bot_wallet_summary(self) -> str:
        try:
            w = self.ledger.find(self.BOT_WALLET_NAME)
        except Exception:
            return "Wallet bot non initialisé."
        prices = self.engine.prices()
        equity = self.ledger.equity(w["id"], prices)
        bals = self.ledger.balances(w["id"])
        lines = [f"**{self.BOT_WALLET_NAME}** · Equity **{equity:,.2f} USDT**",
                 f"État système: `{self.safety.state.name}` · Source: `{self.provider.source}`"]
        for asset, qty in bals.items():
            if asset == "USDT":
                lines.append(f"• USDT libre: `{float(qty):,.2f}`")
            else:
                px = prices.get(f"{asset}/USDT", 0)
                lines.append(f"• {asset}: `{float(qty):.6f}` ≈ `{float(qty)*px:,.2f} USDT`")
        return "\n".join(lines)

    def run_bot_strategy(self) -> str:
        if self.safety.state.name in ("HALT", "ENTRY_LOCK", "EXIT_ONLY"):
            return f"Stratégie bloquée (état={self.safety.state.name})"
        try:
            w = self.ledger.find(self.BOT_WALLET_NAME)
        except Exception:
            return "Wallet bot absent"
        actions = []
        for sym in SYMBOLS[:4]:
            try:
                cs = self.provider.candles(sym, n=50)
                closes = [c.c for c in cs]
                if len(closes) < 30: continue
                sma_fast = sum(closes[-10:]) / 10
                sma_slow = sum(closes[-30:]) / 30
                last = closes[-1]
                bals = self.ledger.balances(w["id"])
                usdt = float(bals.get("USDT", 0))
                base = sym.split("/")[0]
                pos = float(bals.get(base, 0))
                if sma_fast > sma_slow * 1.002 and pos == 0 and usdt > 50:
                    qty = (usdt * 0.15) / last
                    r = self.engine.submit(self.BOT_WALLET_NAME, sym, "buy", str(round(qty, 6)), actor="bot-strategy")
                    actions.append(f"BUY {sym} qty≈{qty:.4f} → {r.get('status')}")
                elif sma_fast < sma_slow * 0.998 and pos > 0:
                    r = self.engine.submit(self.BOT_WALLET_NAME, sym, "sell", str(pos), actor="bot-strategy")
                    actions.append(f"SELL {sym} qty={pos:.4f} → {r.get('status')}")
            except Exception as e:
                actions.append(f"{sym}: erreur {type(e).__name__}")
        if not actions:
            return "Aucun signal fort ce cycle (SMA 10/30)."
        return " | ".join(actions)
