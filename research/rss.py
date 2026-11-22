"""Collecteur d'actualités finance via RSS publics."""
from __future__ import annotations
import time, hashlib
from typing import List, Dict
import feedparser

FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("Investing.com", "https://www.investing.com/rss/news.rss"),
]
_seen: set[str] = set()

def fetch_latest(limit_per_feed: int = 5) -> List[Dict]:
    global _seen
    out = []
    for name, url in FEEDS:
        try:
            d = feedparser.parse(url, request_headers={"User-Agent": "V5-Central-Agent/1.0"})
            for e in d.entries[:limit_per_feed]:
                title = getattr(e, "title", "").strip()
                link = getattr(e, "link", "").strip()
                if not title or not link: continue
                h = hashlib.sha256(f"{title}|{link}".encode()).hexdigest()[:16]
                if h in _seen: continue
                _seen.add(h)
                out.append({"source": name, "title": title, "link": link, "summary": getattr(e, "summary", "")[:300], "published": getattr(e, "published", ""), "ts": time.time()})
        except Exception:
            continue
    if len(_seen) > 500: _seen = set(list(_seen)[-250:])
    return out
