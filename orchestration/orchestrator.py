"""Orchestrateur : agents parallèles → contradiction → synthèse."""
import asyncio, json, time
from decimal import Decimal
from agents.analysts import MarketAnalyst, OrderFlowAnalyst, WalletAnalyst, ResearchAnalyst, RiskAnalyst, ContradictionAgent, ChiefAnalyst
from risk.manager import LIMITS
from wallets.ledger import QUOTE

PARALLEL = [MarketAnalyst, OrderFlowAnalyst, WalletAnalyst, ResearchAnalyst, RiskAnalyst]

class Orchestrator:
    def __init__(self, db, ledger, provider, symbols, news_fn=lambda: []):
        self.db, self.ledger, self.provider, self.symbols, self.news_fn = db, ledger, provider, symbols, news_fn

    def build_context(self):
        candles = {s: self.provider.candles(s, 120) for s in self.symbols}
        books = {s: self.provider.book(s) for s in self.symbols} if hasattr(self.provider, "book") else {}
        prices = {s: c[-1].c for s, c in candles.items()}
        wallets = []
        for w in self.ledger.list_wallets():
            eq = self.ledger.equity(w["id"], prices); bal = self.ledger.balances(w["id"]); shares = {}
            for a, q in bal.items():
                if a != QUOTE and eq > 0:
                    shares[a] = float(q * Decimal(str(prices.get(f"{a}/{QUOTE}", 0))) / eq)
            wallets.append({"id": w["id"], "name": w["name"], "equity": float(eq), "positions": {a: str(q) for a, q in bal.items() if a != QUOTE}, "shares": shares})
        return {"candles": candles, "books": books, "wallets": wallets, "news": self.news_fn(), "limits": {k: float(v) for k, v in LIMITS.items()}}

    async def run_analysis(self, trigger="manual"):
        t0 = time.time(); ctx = self.build_context()
        reports = await asyncio.gather(*[asyncio.to_thread(a().run, ctx) for a in PARALLEL])
        reports = list(reports)
        reports.append(ContradictionAgent().run({"reports": reports}))
        reports.append(ChiefAnalyst().run({"reports": reports}))
        out = {"trigger": trigger, "started": t0, "duration": round(time.time()-t0, 3),
               "sources": sorted({c.source for cs in ctx["candles"].values() for c in cs}),
               "reports": [r.to_dict() for r in reports],
               "human_validation_required": any(r.stance == "risk_high" for r in reports)}
        self.db.execute("INSERT INTO reports(kind,body,ts) VALUES(?,?,?)", ("analysis", json.dumps(out, default=str), time.time()))
        self.db.audit("orchestrator", "analysis", {"trigger": trigger})
        return out

def format_report(out) -> str:
    L = [f"**Analyse multi-agents** — {out['trigger']} — sources: {', '.join(out['sources'])}"]
    for r in out["reports"]:
        L.append(f"\n**{r['agent']}** ({r['stance']}, conf {r['confidence']:.0%})" + (f" ⚠️ {r['error']}" if r.get("error") else ""))
        L += [f"• {c['text']}" for c in r["claims"][:3]]
        if r.get("missing_data"): L.append(f"_Manquant: {', '.join(r['missing_data'][:3])}_")
    chief = out["reports"][-1]
    L.append(f"\n**Conclusion**: {chief['claims'][0]['text']}\n**Confiance**: {chief['confidence']:.0%}")
    return "\n".join(L)[:3900]
