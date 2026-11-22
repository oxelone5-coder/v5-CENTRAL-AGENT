"""Structure des catégories / salons Discord – l'interface principale du bot."""
from __future__ import annotations
import discord

LAYOUT = {
    "V5 · 01 Marchés": ["market-overview", "market-data", "order-flow", "charts-live"],
    "V5 · 02 Portefeuille Bot": ["bot-wallet", "paper-trades", "performance"],
    "V5 · 03 Intelligence": ["agent-log", "agent-debates", "signals", "research"],
    "V5 · 04 Actualités": ["news-finance", "macro-events"],
    "V5 · 05 Contrôle": ["control-room", "system-health", "v4-alerts"],
}

PURPOSE = {
    "market-overview": "Dashboard live des prix, variations, top movers",
    "market-data": "Données brutes + source",
    "order-flow": "DOM, CVD approximatif, profondeur",
    "charts-live": "Graphiques générés régulièrement",
    "bot-wallet": "Wallet papier du bot – valorisation temps réel",
    "paper-trades": "Historique des ordres papier",
    "performance": "P&L, drawdown",
    "agent-log": "Journal continu des agents",
    "agent-debates": "Contradictions et synthèses",
    "signals": "Signaux d'investissement (roles mentionnés)",
    "research": "Veille et analyses",
    "news-finance": "Flux d'actualités finance",
    "macro-events": "Événements macro",
    "control-room": "Panneau de contrôle interactif",
    "system-health": "Santé système",
    "v4-alerts": "Alertes",
}

REQUIRED_PERMS = ["manage_channels", "view_channel", "send_messages", "read_message_history",
                  "embed_links", "attach_files", "use_application_commands", "manage_roles", "mention_everyone"]

ROLES_TO_CREATE = [("V4-Signals", 0x00BFFF), ("V4-High-Conviction", 0xFFD700), ("V4-Risk-Alert", 0xFF4500)]


async def ensure_structure(guild: discord.Guild, db):
    created, reused = [], []
    for role_name, color in ROLES_TO_CREATE:
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            try:
                role = await guild.create_role(name=role_name, colour=discord.Colour(color), mentionable=True)
                created.append(f"role:{role_name}")
            except Exception:
                pass
        if role:
            db.execute("INSERT INTO channels(name,channel_id) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET channel_id=excluded.channel_id",
                       (f"role:{role_name}", role.id))
    for cat_name, chans in LAYOUT.items():
        cat = discord.utils.get(guild.categories, name=cat_name)
        if cat is None:
            cat = await guild.create_category(cat_name)
            created.append(f"cat:{cat_name}")
        for name in chans:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch is None:
                ch = await guild.create_text_channel(name, category=cat, topic=PURPOSE.get(name, ""))
                created.append(name)
            else:
                reused.append(name)
            db.execute("INSERT INTO channels(name,channel_id) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET channel_id=excluded.channel_id",
                       (name, ch.id))
    db.audit("system", "ensure_structure", {"created": created, "reused": len(reused)})
    return created, reused


def missing_permissions(perms) -> list:
    return [p for p in REQUIRED_PERMS if not getattr(perms, p, False)]
