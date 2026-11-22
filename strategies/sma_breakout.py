"""SMA20/SMA200 + breakout 20 + ATR14 Wilder, long-only, frais+slippage."""
def atr_wilder(h, l, c, n=14):
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    if len(tr) < n: return [None] * len(tr)
    a = [None] * (n - 1); prev = sum(tr[:n]) / n; a.append(prev)
    for t in tr[n:]: prev = (prev * (n - 1) + t) / n; a.append(prev)
    return a

def backtest(h, l, c, fee=0.001, slip=0.0005, atr_mult=2.0, cash=10000.0):
    atr = atr_wilder(h, l, c); pos = 0.0; entry = stop = 0.0; trades = []; eq = []
    for i in range(len(c)):
        if i >= 200:
            sma20 = sum(c[i - 19:i + 1]) / 20; sma200 = sum(c[i - 199:i + 1]) / 200; hh = max(h[i - 20:i])
            if pos == 0 and c[i] > hh and c[i] > sma200 and c[i] > sma20 and atr[i]:
                px = c[i] * (1 + slip); pos = cash / (px * (1 + fee)); cash -= pos * px * (1 + fee); entry = px; stop = px - atr_mult * atr[i]
            elif pos > 0:
                stop = max(stop, c[i] - atr_mult * atr[i]) if atr[i] else stop
                if c[i] < stop:
                    px = c[i] * (1 - slip); cash += pos * px * (1 - fee); trades.append(px / entry - 1); pos = 0
        eq.append(cash + pos * c[i])
    peak, dd = eq[0], 0.0
    for e in eq: peak = max(peak, e); dd = max(dd, (peak - e) / peak)
    return {"final_equity": eq[-1], "trades": len(trades), "max_drawdown": dd, "buy_hold": c[-1] / c[0] - 1 if c else 0}
