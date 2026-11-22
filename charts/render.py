from __future__ import annotations
import io
from datetime import datetime, timezone
from typing import List, Sequence, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def _fig_bytes(fig) -> bytes:
    b = io.BytesIO()
    fig.savefig(b, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return b.getvalue()

def price_chart(candles, title=None) -> bytes:
    src = candles[-1].source if candles else "?"
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=110, facecolor="#1e1f22")
    ax.set_facecolor("#2b2d31")
    xs = [datetime.fromtimestamp(c.ts, tz=timezone.utc) for c in candles]
    ys = [c.c for c in candles]
    ax.plot(xs, ys, color="#5865F2", lw=1.6)
    ax.fill_between(xs, ys, min(ys)*0.998, color="#5865F2", alpha=0.15)
    ax.set_title(f"{title or candles[-1].symbol}  · {src}", color="white", fontsize=11)
    ax.tick_params(colors="#b5bac1"); ax.grid(alpha=0.25, color="#4e5058")
    for spine in ax.spines.values(): spine.set_color("#4e5058")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    return _fig_bytes(fig)

def setup_chart(candles, sma_fast: Sequence[float], sma_slow: Sequence[float], title="Setup SMA", bias="") -> bytes:
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=110, facecolor="#1e1f22")
    ax.set_facecolor("#2b2d31")
    xs = [datetime.fromtimestamp(c.ts, tz=timezone.utc) for c in candles]
    closes = [c.c for c in candles]
    ax.plot(xs, closes, color="#f2f3f5", lw=1.3, label="Close")
    ax.plot(xs[-len(sma_fast):], list(sma_fast), color="#57F287", lw=1.4, label="SMA10")
    ax.plot(xs[-len(sma_slow):], list(sma_slow), color="#ED4245", lw=1.4, label="SMA30")
    ax.set_title(f"{title}  · biais {bias or 'n/a'}", color="white", fontsize=11)
    ax.legend(facecolor="#2b2d31", labelcolor="white", fontsize=8)
    ax.tick_params(colors="#b5bac1"); ax.grid(alpha=0.25, color="#4e5058")
    for spine in ax.spines.values(): spine.set_color("#4e5058")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    return _fig_bytes(fig)

def equity_chart(points: List[Tuple[float, float]], title="Equity paper") -> bytes:
    fig, ax = plt.subplots(figsize=(9, 4), dpi=110, facecolor="#1e1f22")
    ax.set_facecolor("#2b2d31")
    if not points:
        ax.text(0.5, 0.5, "Pas encore d'historique", ha="center", va="center", color="white")
    else:
        xs = [datetime.fromtimestamp(t, tz=timezone.utc) for t, _ in points]
        ys = [e for _, e in points]
        color = "#57F287" if ys[-1] >= ys[0] else "#ED4245"
        ax.plot(xs, ys, color=color, lw=1.8)
        ax.fill_between(xs, ys, ys[0], color=color, alpha=0.18)
        ax.axhline(ys[0], color="#b5bac1", ls="--", lw=0.8, alpha=0.6)
    ax.set_title(title, color="white", fontsize=11)
    ax.tick_params(colors="#b5bac1"); ax.grid(alpha=0.25, color="#4e5058")
    for spine in ax.spines.values(): spine.set_color("#4e5058")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    return _fig_bytes(fig)

def orderbook_depth(book) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=110, facecolor="#1e1f22")
    ax.set_facecolor("#2b2d31")
    cb=0; xs=[]; ys=[]
    for p,q in book.bids: cb+=q; xs.append(p); ys.append(cb)
    ax.step(xs, ys, where="post", color="#57F287", label="Bids")
    ca=0; xs=[]; ys=[]
    for p,q in book.asks: ca+=q; xs.append(p); ys.append(ca)
    ax.step(xs, ys, where="pre", color="#ED4245", label="Asks")
    ax.set_title(f"Depth {book.symbol} · {book.source}", color="white")
    ax.legend(facecolor="#2b2d31", labelcolor="white", fontsize=8)
    ax.tick_params(colors="#b5bac1"); ax.grid(alpha=0.25, color="#4e5058")
    for spine in ax.spines.values(): spine.set_color("#4e5058")
    return _fig_bytes(fig)
