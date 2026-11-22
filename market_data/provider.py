from __future__ import annotations
import json, os, random, time, urllib.request
from dataclasses import dataclass
SYMBOLS=["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","ADA/USDT","BNB/USDT","DOGE/USDT"]
_BASE={"BTC/USDT":95000.,"ETH/USDT":3400.,"SOL/USDT":180.,"XRP/USDT":0.62,"ADA/USDT":0.55,"BNB/USDT":620.,"DOGE/USDT":0.18}
DEFAULT_HOST="https://data-api.binance.vision"
class _Degraded(Exception): pass
@dataclass(frozen=True)
class Candle:
    symbol:str; ts:int; o:float; h:float; l:float; c:float; v:float; source:str
@dataclass(frozen=True)
class BookSnapshot:
    symbol:str; ts:float; bids:list; asks:list; source:str
class SyntheticProvider:
    source="SYNTHETIC"
    def __init__(self, seed=42): self.seed=seed
    def candles(self, symbol, n=100, step=300, end_ts=None):
        end_ts=int(end_ts or time.time()); rnd=random.Random(f"{self.seed}:{symbol}"); p=_BASE.get(symbol,100.); out=[]
        for i in range(n):
            o=p; c=o*(1+rnd.gauss(0.0001,0.004)); h=max(o,c)*(1+abs(rnd.gauss(0,0.0015))); l=min(o,c)*(1-abs(rnd.gauss(0,0.0015)))
            out.append(Candle(symbol,end_ts-(n-i)*step,o,h,l,c,abs(rnd.gauss(100,30)),self.source)); p=c
        return out
    def last_price(self,s): return self.candles(s,30)[-1].c
    def book(self,s,depth=10):
        mid=self.last_price(s)
        return BookSnapshot(s,time.time(),[(mid*(1-0.0004*(i+1)),1.) for i in range(depth)],[(mid*(1+0.0004*(i+1)),1.) for i in range(depth)],self.source)
    def ticker(self,s):
        c=self.candles(s,20); return {"symbol":s,"price":c[-1].c,"change_pct":(c[-1].c-c[0].c)/c[0].c*100 if c[0].c else 0,"source":self.source}
class PublicExchangeProvider:
    source="LIVE_PUBLIC"; COOLDOWN=900
    def __init__(self, host=DEFAULT_HOST):
        self.host=(host or DEFAULT_HOST).rstrip("/"); self._syn=SyntheticProvider(); self._down_until=0.
    def _src(self): return "SYNTHETIC(fallback)" if time.time()<self._down_until else self.source
    def _get(self, path, timeout=8):
        if time.time()<self._down_until: raise _Degraded()
        req=urllib.request.Request(self.host+path, headers={"User-Agent":"V5-Central-Agent/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
        except Exception:
            self._down_until=time.time()+self.COOLDOWN; raise _Degraded()
    def candles(self, symbol, n=100, **_):
        try: rows=self._get(f"/api/v3/klines?symbol={symbol.replace('/','')}&interval=5m&limit={n}")
        except _Degraded: return self._syn.candles(symbol,n)
        return [Candle(symbol,int(k[0]//1000),float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5]),self._src()) for k in rows]
    def last_price(self,s): return self.candles(s,2)[-1].c
    def book(self,s,depth=10):
        try:
            d=self._get(f"/api/v3/depth?symbol={s.replace('/','')}&limit={depth}")
            return BookSnapshot(s,time.time(),[(float(p),float(q)) for p,q in d.get("bids",[])],[(float(p),float(q)) for p,q in d.get("asks",[])],self.source)
        except Exception:
            mid=self.last_price(s)
            return BookSnapshot(s,time.time(),[(mid*(1-0.0004*(i+1)),1.) for i in range(depth)],[(mid*(1+0.0004*(i+1)),1.) for i in range(depth)],self._src())
    def ticker(self,s):
        try: d=self._get(f"/api/v3/ticker/24hr?symbol={s.replace('/','')}")
        except _Degraded:
            t=self._syn.ticker(s); t["source"]="SYNTHETIC(fallback)"; return t
        return {"symbol":s,"price":float(d["lastPrice"]),"change_pct":float(d["priceChangePercent"]),"source":self.source}
def get_provider(live=False):
    return PublicExchangeProvider(os.environ.get("V4_MARKET_HOST", DEFAULT_HOST)) if live else SyntheticProvider()
