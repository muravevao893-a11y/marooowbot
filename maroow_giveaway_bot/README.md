# &marooow bot + Premium Mini App v3

Telegram bot with channel comment drops, referrals, Stars top-up, and a premium Telegram Mini App UI.

## Что внутри

- Premium Mini App `/app` with dark casino-style UI.
- Telegram auth via Mini App initData.
- Telegram profile import: id, first name, username, optional photo_url.
- Internal profile: balance, level, EXP, referrals, chance.
- Stars top-up invoice for Mini App internal balance.
- Telegram Gifts catalog from `getAvailableGifts` with media proxy fallback.
- Inventory of gifts won inside &marooow.
- Premium SVG/CSS icons, polished cards and bottom tabs.
- Fan mini-games/cases screens as event/demo modes.

## Важно

This project intentionally does not implement real-money casino mechanics, cash-out, or paid random lootboxes. Cases and games are UI/event modes. Telegram gifts are issued by the bot according to bot drop rules.

## Railway

Start command:

```bash
python -m app.main
```

Variables:

```env
BOT_TOKEN=...
BOT_USERNAME=marooowbot
CHANNEL_ID=-100...
DISCUSSION_CHAT_ID=-100...
ADMIN_IDS=...
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
REDIS_URL=${{Redis.REDIS_URL}}
WEBAPP_ENABLED=true
MINI_APP_URL=https://your-domain.up.railway.app/app
```

Mini App health:

```text
https://your-domain.up.railway.app/api/health
```

BotFather cover: `assets/miniapp_cover_640x360.jpg`.
