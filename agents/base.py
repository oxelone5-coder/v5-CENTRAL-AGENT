import time
from dataclasses import dataclass, field, asdict

@dataclass
class Claim:
    text: str
    evidence: list

@dataclass
class AgentReport:
    agent: str
    role: str
    stance: str
    claims: list = field(default_factory=list)
    confidence: float = 0.0
    confidence_basis: str = ""
    limits: list = field(default_factory=list)
    missing_data: list = field(default_factory=list)
    ts: float = field(default_factory=time.time)
    error: str = ""
    def to_dict(self): return asdict(self)

class Agent:
    name = "agent"; role = ""; objective = ""; reads = ()
    def run(self, ctx: dict) -> AgentReport:
        view = {k: ctx[k] for k in self.reads if k in ctx}
        try:
            return self.analyze(view)
        except Exception as e:
            return AgentReport(self.name, self.role, "n/a", error=str(e), limits=["échec agent"])
    def analyze(self, view) -> AgentReport: raise NotImplementedError

def sma(vals, n): return sum(vals[-n:]) / n if len(vals) >= n else None
def ev(symbol, c): return f"{symbol} close={c.c:.4f} ts={int(c.ts)} source={c.source}"
