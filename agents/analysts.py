import statistics
from agents.base import Agent, AgentReport, Claim, sma, ev

class MarketAnalyst(Agent):
    name = "market_analyst"; role = "Marché"; reads = ("candles",)
    def analyze(self, v):
        claims, votes, miss = [], [], []
        for s, cs in v["candles"].items():
            if len(cs) < 30: miss.append(f"{s}: historique insuffisant"); continue
            closes = [c.c for c in cs]; fast, slow = sma(closes, 10), sma(closes, 30)
            vol = statistics.pstdev([(closes[i]/closes[i-1])-1 for i in range(1, len(closes))])
            trend = "haussière" if fast > slow else "baissière"; votes.append(1 if fast > slow else -1)
            claims.append(Claim(f"{s}: tendance {trend} (SMA10 {fast:.4f} vs SMA30 {slow:.4f}), vol {vol:.4%}", [ev(s, cs[-1])]))
        score = sum(votes); stance = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
        conf = 0.0 if not votes else min(0.7, 0.3 + 0.1 * abs(score))
        return AgentReport(self.name, self.role, stance, claims, conf, "Heuristique SMA10/30", ["Indicateur à retard"], miss)

class OrderFlowAnalyst(Agent):
    name = "orderflow_analyst"; role = "Microstructure"; reads = ("books", "candles")
    def analyze(self, v):
        claims, imb, miss = [], [], []
        for s, b in v.get("books", {}).items():
            bv = sum(q for _, q in b.bids); av = sum(q for _, q in b.asks); i = (bv - av) / (bv + av + 1e-9)
            imb.append(i)
            claims.append(Claim(f"{s}: déséquilibre carnet {i:+.2%}", [f"{s} book source={b.source}"]))
        for s, cs in v.get("candles", {}).items():
            cvd = sum((1 if c.c >= c.o else -1) * c.v for c in cs[-50:])
            claims.append(Claim(f"{s}: CVD approx = {cvd:+.1f}", [ev(s, cs[-1])]))
        if not imb: miss.append("carnet")
        m = sum(imb)/len(imb) if imb else 0
        return AgentReport(self.name, self.role, "bullish" if m > 0.05 else "bearish" if m < -0.05 else "neutral", claims, 0.25 if imb else 0.0, "Carnet limité", ["CVD approximé"], miss)

class WalletAnalyst(Agent):
    name = "wallet_analyst"; role = "Portefeuille"; reads = ("wallets",)
    def analyze(self, v):
        claims = [Claim(f"{x['name']}: equity {x.get('equity',0):.2f} USDT", [f"ledger={x['id']}"]) for x in v.get("wallets", [])]
        return AgentReport(self.name, self.role, "neutral", claims, 0.6 if claims else 0.0, "Lecture ledger", [], [] if claims else ["aucun wallet"])

class ResearchAnalyst(Agent):
    name = "research_analyst"; role = "Recherche"; reads = ("news",)
    def analyze(self, v):
        items = [n for n in v.get("news", []) if n.get("title")]
        claims = [Claim(f"[{n['source']}] {n['title'][:120]}", [f"url={n.get('link','?')}"]) for n in items[:5]]
        return AgentReport(self.name, self.role, "neutral" if items else "n/a", claims, 0.0, "Données non fiables", ["Pas de sentiment"], [] if items else ["aucune news"])

class RiskAnalyst(Agent):
    name = "risk_analyst"; role = "Risque"; reads = ("wallets", "limits")
    def analyze(self, v):
        claims, hi = [], False; lim = float(v.get("limits", {}).get("max_position_pct", 0.4))
        for x in v.get("wallets", []):
            for sym, share in x.get("shares", {}).items():
                if share > lim: hi = True
                claims.append(Claim(f"{x['name']}: {sym} = {share:.1%}", [f"ledger={x['id']}"]))
        return AgentReport(self.name, self.role, "risk_high" if hi else "risk_ok", claims, 0.8 if claims else 0.0, "Règle déterministe", [], [])

class ContradictionAgent(Agent):
    name = "contradiction_agent"; role = "Contre-analyse"; reads = ("reports",)
    def analyze(self, v):
        rs = v.get("reports", []); claims = []; miss = []
        stances = {r.agent: r.stance for r in rs if r.stance in ("bullish", "bearish")}
        if len(set(stances.values())) > 1: claims.append(Claim(f"Désaccord : {stances}", ["reports"]))
        for r in rs:
            if r.error: claims.append(Claim(f"{r.agent} erreur : {r.error}", ["reports"]))
            miss += [f"{r.agent}: {m}" for m in r.missing_data]
        return AgentReport(self.name, self.role, "neutral", claims, 0.0, "Rôle critique", [], miss)

class ChiefAnalyst(Agent):
    name = "chief_analyst"; role = "Synthèse"; reads = ("reports",)
    def analyze(self, v):
        rs = v.get("reports", [])
        dirs = [r for r in rs if r.stance in ("bullish", "bearish") and not r.error]
        bull = sum(r.confidence for r in dirs if r.stance == "bullish")
        bear = sum(r.confidence for r in dirs if r.stance == "bearish")
        risk_hi = any(r.stance == "risk_high" for r in rs)
        if not dirs: concl, stance = "Données insuffisantes.", "n/a"
        elif abs(bull - bear) < 0.15: concl, stance = "Signaux partagés.", "neutral"
        else: stance = "bullish" if bull > bear else "bearish"; concl = f"Scénario {'haussier' if stance=='bullish' else 'baissier'} favorisé."
        if risk_hi: concl += " ATTENTION concentration."
        conf = min(0.5, abs(bull - bear)/2) if dirs else 0.0
        claims = [Claim(concl, [f"{r.agent}:{r.stance}:{r.confidence:.2f}" for r in rs])]
        return AgentReport(self.name, self.role, stance, claims, round(conf, 2), "Pondération confiances agents", ["Invalidation SMA ou limite risque"], [m for r in rs for m in r.missing_data])
