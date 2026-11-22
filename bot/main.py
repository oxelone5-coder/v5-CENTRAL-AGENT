"""
V5 Central Agent – point d'entrée ultra-actif.
Toute l'interface et l'activité des agents sont retranscrites dans les salons Discord.
Le bot ne se contente pas d'attendre des commandes : il publie, met à jour, analyse et trade en continu.
"""
from __future__ import annotations
import asyncio
import io
import logging
import time
from datetime import datetime, timezone

import discord
from discord import app_commands

from config.settings import load_settings
from security.redact import setup_logging
from database.db import Database
from wallets.ledger import Ledger
from risk.safety import SafetyController
from risk.manager import RiskManager
from paper_execution.engine import PaperExecutionEngine
from market_data.provider import get_provider, SYMBOLS
from orchestration.orchestrator import Orchestrator
from bot.services import Services, HELP
from discord_ui.layout import ensure_structure, missing_permissions
from research.rss import fetch_latest
from charts.render import price_chart, orderbook_depth

log = logging.getLogger("v5")


def build_services(settings):
    db = Database(settings.db_path)
    ledger = Ledger(db)
    safety = SafetyController(db)
    provider = get_provider(settings.live_public)
    engine = PaperExecutionEngine(db, ledger, RiskManager(ledger, safety), provider)
    orch = Orchestrator(db, ledger, provider, SYMBOLS)
    return Services(settings, db, ledger, engine, safety, orch, provider)


def run():
    setup_logging()
    st = load_settings()
    svc = build_services(st)

    class ControlPanel(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="🔄 Statut", custom_id="v5:status", style=discord.ButtonStyle.primary, row=0)
        async def status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(svc.status(), ephemeral=True)

        @discord.ui.button(label="📊 Marché", custom_id="v5:market", style=discord.ButtonStyle.secondary, row=0)
        async def market_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(svc.market(), ephemeral=True)

        @discord.ui.button(label="🧠 Analyser", custom_id="v5:analyze", style=discord.ButtonStyle.success, row=0)
        async def analyze_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            txt = await svc.analyze("button")
            await interaction.followup.send(txt[:1900], ephemeral=True)

        @discord.ui.button(label="💼 Wallet Bot", custom_id="v5:wallet", style=discord.ButtonStyle.secondary, row=1)
        async def wallet_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(svc.bot_wallet_summary(), ephemeral=True)

        @discord.ui.button(label="⏸ Pause", custom_id="v5:pause", style=discord.ButtonStyle.danger, row=1)
        async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != st.owner_id:
                return await interaction.response.send_message("Owner only", ephemeral=True)
            await interaction.response.send_message(svc.pause(interaction.user.id), ephemeral=True)

    class Bot(discord.Client):
        def __init__(self):
            intents = discord.Intents.default()
            intents.guilds = True
            intents.message_content = True
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)
            self._dash_msg: dict[str, int] = {}

        async def setup_hook(self):
            self.add_view(ControlPanel())
            g = discord.Object(id=st.guild_id)
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
            self.loop.create_task(self.background_loop())

        async def on_ready(self):
            log.info("Connecté en tant que %s (id=%s)", self.user, self.user.id)
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name="marchés · agents 24/7")
            )

        async def get_chan(self, name: str):
            row = svc.db.execute("SELECT channel_id FROM channels WHERE name=?", (name,)).fetchone()
            if not row:
                return None
            return self.get_channel(row["channel_id"])

        async def get_role(self, name: str):
            row = svc.db.execute("SELECT channel_id FROM channels WHERE name=?", (f"role:{name}",)).fetchone()
            if not row or not row["channel_id"]:
                return None
            g = self.get_guild(st.guild_id)
            return g.get_role(row["channel_id"]) if g else None

        async def safe_send(self, channel_name: str, content: str = None, embed: discord.Embed = None,
                            file: discord.File = None, view: discord.ui.View = None):
            ch = await self.get_chan(channel_name)
            if ch is None:
                return None
            try:
                kwargs = {}
                if content:
                    kwargs["content"] = content[:2000]
                if embed:
                    kwargs["embed"] = embed
                if file:
                    kwargs["file"] = file
                if view:
                    kwargs["view"] = view
                return await ch.send(**kwargs)
            except Exception as e:
                log.warning("safe_send %s: %s", channel_name, e)
                return None

        async def safe_edit_or_send(self, channel_name: str, embed: discord.Embed, key: str = "default"):
            ch = await self.get_chan(channel_name)
            if ch is None:
                return
            msg_id = self._dash_msg.get(f"{channel_name}:{key}")
            if msg_id:
                try:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                    return
                except Exception:
                    pass
            try:
                msg = await ch.send(embed=embed)
                self._dash_msg[f"{channel_name}:{key}"] = msg.id
            except Exception as e:
                log.warning("edit_or_send %s: %s", channel_name, e)

        async def background_loop(self):
            await self.wait_until_ready()
            guild = self.get_guild(st.guild_id)
            if guild is None:
                log.error("Serveur %s introuvable – bot non invité ?", st.guild_id)
                return

            miss = missing_permissions(guild.me.guild_permissions)
            created, reused = await ensure_structure(guild, svc.db)
            log.info("Structure Discord: created=%s reused=%s", created, len(reused))

            if miss:
                await self.safe_send("v4-alerts", f"⚠️ Permissions manquantes: {', '.join(miss)}")

            await self.safe_send(
                "control-room",
                content="**V5 Central Agent – Panneau de contrôle**\nLe bot tourne en mode autonome 24/7. Utilise les boutons ou les commandes `/v5`.",
                view=ControlPanel()
            )

            try:
                svc.ensure_bot_wallet(st.bot_wallet_capital)
            except Exception as e:
                log.warning("ensure_bot_wallet: %s", e)

            last_market = last_analysis = last_strategy = last_news = last_portfolio = 0
            tick = 0

            while not self.is_closed():
                now = time.time()
                svc.db.set_config("heartbeat", now)
                tick += 1

                try:
                    if now - last_market >= st.market_interval:
                        last_market = now
                        await self.update_market_dashboard()

                    if now - last_analysis >= st.analysis_interval:
                        last_analysis = now
                        await self.run_agents_cycle()

                    if now - last_strategy >= st.strategy_interval:
                        last_strategy = now
                        await self.run_strategy_cycle()

                    if now - last_news >= st.news_interval:
                        last_news = now
                        await self.push_news()

                    if now - last_portfolio >= st.portfolio_interval:
                        last_portfolio = now
                        await self.update_portfolio()

                    if tick % 20 == 0:
                        await self.safe_send("system-health", f"❤️ Heartbeat {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} · tick={tick}")

                except Exception:
                    log.exception("Erreur dans background_loop")

                await asyncio.sleep(30)

        async def update_market_dashboard(self):
            lines = []
            for sym in SYMBOLS[:6]:
                try:
                    t = svc.provider.ticker(sym)
                    emoji = "🟢" if t.get("change_pct", 0) >= 0 else "🔴"
                    lines.append(f"{emoji} **{sym}** `{t['price']:,.4f}` ({t.get('change_pct', 0):+.2f}%) · `{t.get('source', '?')}`")
                except Exception:
                    lines.append(f"⚪ **{sym}** indisponible")

            embed = discord.Embed(
                title="📈 Market Overview (live)",
                description="\n".join(lines),
                color=0x00BFFF,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"Source: {'LIVE_PUBLIC (Binance)' if st.live_public else 'SYNTHETIC'} · auto-update")
            await self.safe_edit_or_send("market-overview", embed, key="main")

            try:
                candles = svc.provider.candles("BTC/USDT", n=60)
                img = price_chart(candles, title="BTC/USDT 5m")
                ch = await self.get_chan("charts-live")
                if ch and img:
                    await ch.send(file=discord.File(io.BytesIO(img), "btc.png"),
                                  content=f"📊 BTC/USDT · {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
            except Exception as e:
                log.debug("chart: %s", e)

        async def run_agents_cycle(self):
            try:
                report = await svc.analyze("scheduled")
                embed = discord.Embed(
                    title="🧠 Cycle Agents terminé",
                    description=report[:3500],
                    color=0x9B59B6,
                    timestamp=datetime.now(timezone.utc),
                )
                await self.safe_send("agent-log", embed=embed)

                if "BUY" in report.upper() or "LONG" in report.upper():
                    role = await self.get_role("V4-Signals")
                    mention = role.mention if role else "@here"
                    await self.safe_send("signals", f"{mention} 📡 Signal détecté par les agents – voir #agent-log")
            except Exception:
                log.exception("run_agents_cycle")

        async def run_strategy_cycle(self):
            try:
                result = svc.run_bot_strategy()
                if result:
                    embed = discord.Embed(
                        title="🤖 Action Stratégie Bot",
                        description=result[:2000],
                        color=0x2ECC71,
                        timestamp=datetime.now(timezone.utc),
                    )
                    await self.safe_send("paper-trades", embed=embed)
                    await self.update_portfolio()
            except Exception:
                log.exception("run_strategy_cycle")

        async def push_news(self):
            articles = fetch_latest(limit_per_feed=3)
            for a in articles[:8]:
                embed = discord.Embed(
                    title=a["title"][:250],
                    url=a["link"],
                    description=(a.get("summary") or "")[:400],
                    color=0x3498DB,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_author(name=a["source"])
                await self.safe_send("news-finance", embed=embed)
                await asyncio.sleep(1.2)

        async def update_portfolio(self):
            summary = svc.bot_wallet_summary()
            embed = discord.Embed(
                title="💼 Wallet Papier du Bot",
                description=summary[:3500],
                color=0xF1C40F,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="Capital fictif · prix réels (ou synthetic) · aucun ordre réel envoyé")
            await self.safe_edit_or_send("bot-wallet", embed, key="main")

    bot = Bot()
    grp = app_commands.Group(name="v5", description="V5 Central Agent")

    async def guard(inter: discord.Interaction, fn, *a):
        try:
            r = fn(*a)
            r = await r if asyncio.iscoroutine(r) else r
        except PermissionError as e:
            r = f"⛔ {e}"
        except Exception as e:
            log.exception("commande échouée")
            r = f"Erreur: {type(e).__name__}: {e}"
        if inter.response.is_done():
            await inter.followup.send(str(r)[:1900], ephemeral=True)
        else:
            await inter.response.send_message(str(r)[:1900], ephemeral=True)

    uid = lambda i: i.user.id

    @grp.command(name="help")
    async def _h(i: discord.Interaction):
        await guard(i, lambda: HELP)

    @grp.command(name="status")
    async def _s(i: discord.Interaction):
        await guard(i, svc.status)

    @grp.command(name="market")
    async def _m(i: discord.Interaction):
        await guard(i, svc.market)

    @grp.command(name="portfolio")
    async def _po(i: discord.Interaction):
        await guard(i, svc.bot_wallet_summary)

    @grp.command(name="analyze")
    async def _a(i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await guard(i, svc.analyze, "slash")

    @grp.command(name="pause")
    async def _pa(i: discord.Interaction):
        await guard(i, svc.pause, uid(i))

    @grp.command(name="resume")
    async def _re(i: discord.Interaction):
        await guard(i, svc.resume, uid(i))

    @grp.command(name="emergency_halt")
    async def _eh(i: discord.Interaction):
        await guard(i, svc.emergency_halt, uid(i))

    bot.tree.add_command(grp)
    bot.run(st.token)


if __name__ == "__main__":
    run()
