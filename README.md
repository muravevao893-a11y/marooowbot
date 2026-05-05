# maroow giveaway bot — final

Railway-ready Telegram bot for channel comment drops.

## Features

- Auto-drop message under every new channel post in linked discussion chat
- Chance-based teddy bear drop per valid comment
- Winner reply with "claim gift" button
- Admins are excluded from winning
- Referral system: +0.1% chance per active referral, capped
- Referral activation requires comments under multiple posts
- Anti-spam: cooldown, hourly limit, duplicate text protection
- Pretty HTML messages
- Commands: /start /profile /chance /winners /refs /activity /rules
- Admin: /admin /stats /drop
- Stars: /balance /topup /gifts
- Safe SQLAlchemy models without fragile relationships/back_populates
- DB migrations for old Railway schemas

## Railway

Start command:

```bash
python -m app.main
```

Important variables:

```env
BOT_TOKEN=
BOT_USERNAME=marooowbot
ADMIN_IDS=1087968824
CHANNEL_ID=-1003791124367
DISCUSSION_CHAT_ID=-1003976665797
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
REDIS_URL=${{Redis.REDIS_URL}}
AUTO_DROPS_ENABLED=true
AUTO_DROP_GIFT_ID=
CHANCE_DROP_PERCENT=3
```

Use one minus before `-100...` IDs.

## Telegram setup

1. Add bot as admin to channel.
2. Add bot as admin to discussion group.
3. Disable privacy mode via @BotFather → /setprivacy → Disable.
4. Publish a new channel post.
