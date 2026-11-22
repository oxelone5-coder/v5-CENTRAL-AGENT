"""Fournisseurs de données. SOURCE : SYNTHETIC | LIVE_PUBLIC."""
from __future__ import annotations
import json, random, time, urllib.request
from dataclasses import dataclass
from typing import List, Optional

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "BNB/USDT", "DOGE/USDT"]
_BASE = {"BTC/USDT": 95000.0, "ETH/USDT": 3400.0, "SOL/USDT": 180.0, "XRP/USDT": 0.62, "ADA/USDT": 0.55, "BNB/USDT": 620.0, "DOGE/USDT": 0.18}

@dataclass(frozen=True)
class Candle:
    symbol: str; ts: int; o: float; h: float; l: float; c: float; v: float; source: str

@dataclass(frozen=True)
class BookSnapshot:
    symbol: str; ts: float; bids: list; asks: list; source: str

class SyntheticProvider:
    source = "SYNTHETIC"
    def __init__(self, seed=42): self.seed = seed
    def candles(self, symbol: str, n: int = 200, step: int = 300, end_ts: Optional[int] = None) -> List[Candle]:
        end_ts = int(end_ts or time.time()); rnd = random.Random(f"{self.seed}:{symbol}"); p = _BASE.get(symbol, 100.0); out = []
        for i in range(n):
            o = p; drift = rnd.gauss(0.0001, 0.004); c = o * (1 + drift)
            h = max(o, c) * (1 + abs(rnd.gauss(0, 0.0015))); l = min(o, c) * (1 - abs(rnd.gauss(0, 0.0015)))
            out.append(Candle(symbol, end_ts - (n - i) * step, o, h, l, c, abs(rnd.gauss(100, 30)), self.source)); p = c
        return out
    def last_price(self, symbol: str) -> float: return self.candles(symbol, 50)[-1].c
    def book(self, symbol: str, depth: int = 10) -> BookSnapshot:
        mid = self.last_price(symbol); rnd = random.Random(f"{self.seed}:book:{symbol}")
        bids = [(mid * (1 - 0.0005 * (i + 1)), round(rnd.uniform(0.5, 5), 3)) for i in range(depth)]
        asks = [(mid * (1 + 0.0005 * (i + 1)), round(rnd.uniform(0.5, 5), 3)) for i in range(depth)]
        return BookSnapshot(symbol, time.time(), bids, asks, self.source)
    def ticker(self, symbol: str) -> dict:
        c = self.candles(symbol, 30); last = c[-1].c; prev = c[0].c
        return {"symbol": symbol, "price": last, "change_pct": (last - prev) / prev * 100 if prev else 0, "source": self.source}

class PublicExchangeProvider:
    source = "LIVE_PUBLIC"
    KLINES = "https://api.binance.com/api/v3/klines?symbol={s}&interval=5m&limit={n}"
    TICKER = "https://api.binance.com/api/v3/ticker/24hr?symbol={s}"
    def _get(self, url: str, timeout: int = 8):
        req = urllib.request.Request(url, headers={"User-Agent": "V5-Central-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    def candles(self, symbol: str, n: int = 100, **_) -> List[Candle]:
        s = symbol.replace("/", ""); rows = self._get(self.KLINES.format(s=s, n=n))
        return [Candle(symbol, int(k[0] // 1000), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), self.source) for k in rows]
    def last_price(self, symbol: str) -> float: return self.candles(symbol, 2)[-1].c
    def book(self, symbol: str, depth: int = 10) -> BookSnapshot:
        mid = self.last_price(symbol)
        return BookSnapshot(symbol, time.time(), [(mid * (1 - 0.0004 * (i + 1)), 1.0) for i in range(depth)], [(mid * (1 + 0.0004 * (i + 1)), 1.0) for i in range(depth)], self.source)
    def ticker(self, symbol: str) -> dict:
        s = symbol.replace("/", "")
        try:
            d = self._get(self.TICKER.format(s=s))
            return {"symbol": symbol, "price": float(d["lastPrice"]), "change_pct": float(d["priceChangePercent"]), "high": float(d["highPrice"]), "low": float(d["lowPrice"]), "volume": float(d["volume"]), "source": self.source}
        except Exception:
            return {"symbol": symbol, "price": self.last_price(symbol), "change_pct": 0.0, "source": self.source}

def get_provider(live: bool = False):
    return PublicExchangeProvider() if live else SyntheticProvider()
