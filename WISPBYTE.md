# Déploiement Wispbyte — v5-CENTRAL-AGENT

## Serveur déjà lié
- Déploiement: **v4-trading-core**
- Repo: `oxelone5-coder/v5-CENTRAL-AGENT` branche `main`
- Action: **Pull · Installer · Redémarrer** à chaque push sur main

## Startup Command (panel)
```bash
bash start.sh
```
ou:
```bash
python -m pip install --user -r requirements.txt && python -u -m bot.main
```

## Variables d'environnement (Startup → Env)
Obligatoire:
- `DISCORD_BOT_TOKEN` = token bot (reset recommandé si exposé)
- `V4_GUILD_ID=1094687434756862013`
- `V4_OWNER_ID=643118671383756849`
- `V4_APP_ID=1573506462787838163`

Recommandé:
- `V4_LIVE_PUBLIC=1`
- `V4_BOT_WALLET_CAPITAL=10000`
- `V4_SHAWKY_ID=1171534592281432144`
- `V4_MARIUS_ID=1309980916730429463`

**Ne jamais committer le token.** Utiliser les env du panel ou un `.env` local non versionné.

## Après push
1. Bouton **Déployer** sur Wispbyte (ou attendre le prochain push auto)
2. Console → vérifier `Connecté en tant que …`
3. Discord: cycles paper-trades + charts
