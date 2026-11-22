import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def price_chart(candles, title=None) -> bytes:
    src = candles[-1].source
    fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
    ax.plot([c.ts for c in candles], [c.c for c in candles], lw=1.2)
    ax.set_title(f"{title or candles[-1].symbol}  [source: {src}]"); ax.grid(alpha=.3)
    b = io.BytesIO(); fig.savefig(b, format="png", bbox_inches="tight"); plt.close(fig); return b.getvalue()

def orderbook_depth(book) -> bytes:
    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=100)
    cb = 0; xs, ys = [], []
    for p, q in book.bids: cb += q; xs.append(p); ys.append(cb)
    ax.step(xs, ys, where="post", color="g")
    ca = 0; xs, ys = [], []
    for p, q in book.asks: ca += q; xs.append(p); ys.append(ca)
    ax.step(xs, ys, where="pre", color="r"); ax.set_title(f"Depth {book.symbol} [source: {book.source}]")
    b = io.BytesIO(); fig.savefig(b, format="png", bbox_inches="tight"); plt.close(fig); return b.getvalue()
