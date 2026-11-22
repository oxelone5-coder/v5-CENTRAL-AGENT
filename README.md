# V5 Central Agent

Bot Discord **ultra-actif** de paper-trading multi-agents.

L'interface = les salons Discord. Le bot crée et maintient toute la structure, publie en continu des embeds, graphiques, analyses d'agents, actualités et trades sur son propre wallet papier.

## Fonctionnalités clés

- **Interfaces Discord riches** : embeds live édités, boutons persistants, graphiques matplotlib, catégories + salons auto-créés.
- **Activité 24/7** : le bot ne se contente pas d'attendre des commandes. Il met à jour le marché, lance les agents, poste des news et trade tout seul.
- **Wallet papier du bot** : capital initial configurable (défaut 10 000 USDT), marqué aux prix réels (Binance public) ou synthetic.
- **Agents déterministes** (Market, OrderFlow, Research, Risk, Contradiction, Chief) qui tournent en boucle.
- **Salon d'actualités finance** alimenté en continu (RSS publics).
- **Rôles** `V4-Signals`, `V4-High-Conviction`, `V4-Risk-Alert` créés et mentionnés.
- **Paper-only** : aucun ordre réel n'est jamais envoyé à un exchange.

## Déploiement (Linux)

```bash
git clone https://github.com/oxelone5-coder/v5-CENTRAL-AGENT.git
cd v5-CENTRAL-AGENT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # mettre DISCORD_BOT_TOKEN + vérifier les IDs
mkdir -p data
python -m bot.main
```

Ou avec Docker :

```bash
cp .env.example .env
# éditer .env
docker compose up -d --build
```

## Permissions Discord requises

Manage Channels, Manage Roles, View Channels, Send Messages, Read Message History, Embed Links, Attach Files, Use Application Commands, Mention Everyone (pour les signaux).

## Sécurité

- Le token n'est **jamais** dans le code ni dans le dépôt.
- Tout est paper-trading.
- Les contenus externes (news) sont traités comme non fiables.

## Structure des salons (auto-créée)

- **V4 · 01 Marchés** : market-overview, market-data, order-flow, charts-live
- **V4 · 02 Portefeuille Bot** : bot-wallet, paper-trades, performance
- **V4 · 03 Intelligence** : agent-log, agent-debates, signals, research
- **V4 · 04 Actualités** : news-finance, macro-events
- **V4 · 05 Contrôle** : control-room, system-health, v4-alerts

## Commandes principales

`/v4 status` · `/v4 market` · `/v4 portfolio` · `/v4 analyze` · `/v4 pause` · `/v4 resume` · `/v4 emergency_halt`

Le panneau de contrôle dans `#control-room` offre aussi des boutons interactifs.
