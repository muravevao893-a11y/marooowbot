# &marooow Telegram Bot + Mini App

Railway-ready проект: Telegram bot + WebApp/Mini App.

## Что есть

- авто-дроп под каждым новым постом канала;
- шанс выпадения подарка за комментарий;
- рефералка +0.1% к шансу за активного рефа;
- антиспам/cooldown;
- выдача подарков через Telegram Gifts;
- /topup, /balance, /gifts;
- Mini App с вкладками: Бесплатно, Пропуск, Игры, Кейсы, Профиль;
- ежедневный бонус внутри Mini App;
- профиль, шанс, реф-ссылка, история победителей, лидерборды;
- безопасные миграции для старой Railway-базы.

## Railway Start Command

```bash
python -m app.main
```

## Важные переменные

```env
BOT_TOKEN=
BOT_USERNAME=marooowbot
ADMIN_IDS=1087968824
CHANNEL_ID=-1003791124367
DISCUSSION_CHAT_ID=-1003976665797
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
REDIS_URL=${{Redis.REDIS_URL}}
MINI_APP_URL=https://YOUR-RAILWAY-DOMAIN.up.railway.app/app
WEBAPP_ENABLED=true
```

После деплоя зайди в BotFather → Bot Settings → Menu Button → Configure menu button и поставь URL из `MINI_APP_URL`.

## Проверка

- `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/health`
- `/start` в боте
- кнопка `🚀 Открыть Mini App`

