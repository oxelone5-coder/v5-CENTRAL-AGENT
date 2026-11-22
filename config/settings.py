"""Configuration centralisée. Le token est lu UNIQUEMENT depuis l'environnement."""
import os
from dataclasses import dataclass

GUILD_ID = 1094687434756862013
APP_ID = 1573506462787838163
OWNER_ID = 643118671383756849
INVITE = "https://discord.gg/QCw7Jnn26"


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"Variable {name} invalide (entier attendu)")


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int
    owner_id: int
    db_path: str
    market_interval: int
    analysis_interval: int
    strategy_interval: int
    news_interval: int
    portfolio_interval: int
    live_public: bool
    bot_wallet_capital: float
    shawky_id: int
    marius_id: int

    def __repr__(self):
        return f"Settings(guild={self.guild_id}, owner={self.owner_id}, token=<redacted>)"


def load_settings(require_token=True) -> Settings:
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if require_token and not token:
        raise RuntimeError("DISCORD_BOT_TOKEN manquant : renseigner .env (voir .env.example)")
    return Settings(
        token=token,
        guild_id=_int("V4_GUILD_ID", GUILD_ID),
        owner_id=_int("V4_OWNER_ID", OWNER_ID),
        db_path=os.environ.get("V4_DB_PATH", "data/v4.sqlite"),
        market_interval=_int("V4_MARKET_INTERVAL", 120),
        analysis_interval=_int("V4_ANALYSIS_INTERVAL", 300),
        strategy_interval=_int("V4_STRATEGY_INTERVAL", 180),
        news_interval=_int("V4_NEWS_INTERVAL", 180),
        portfolio_interval=_int("V4_PORTFOLIO_INTERVAL", 120),
        live_public=os.environ.get("V4_LIVE_PUBLIC", "1") == "1",
        bot_wallet_capital=float(os.environ.get("V4_BOT_WALLET_CAPITAL", "10000")),
        shawky_id=_int("V4_SHAWKY_ID", 0),
        marius_id=_int("V4_MARIUS_ID", 0),
    )
