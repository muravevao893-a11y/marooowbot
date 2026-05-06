# &marooow bot + Premium Mini App v4

Полный бот + Telegram Mini App с премиум UI: дропы в комментариях, рефералка, Stars, TON-пополнение, профиль Telegram, инвентарь подарков проекта и безопасные фан-мини-игры.

## Что добавлено в v4

- Сочный splash/loading screen с анимациями.
- Премиум тёмный интерфейс, SVG-иконки, карточки, анимации кнопок и модальные статусы оплаты.
- Telegram auth через Mini App initData.
- Импорт Telegram profile: id, first_name, username, photo_url если Telegram отдаёт.
- Пополнение через Telegram Stars invoice.
- Пополнение через TON Connect на кошелёк проекта.
- Авто-проверка TON через TonAPI, если указан `TONAPI_KEY`.
- Безопасная идентификация TON-платежей по уникальной сумме в nanotons.
- Красивые статусы: оплата прошла / ожидает проверки / ошибка.
- Каталог доступных Telegram Gifts через `getAvailableGifts`.
- Инвентарь подарков, выигранных внутри &marooow.
- Fan/demo мини-игры без реальных ставок и вывода денег.

## Важно

Это НЕ real-money casino. В проекте нет вывода денег, ставок с реальной ценностью и платных рандом-кейсов с денежным призом. Игры — fan/event режимы. Telegram Gifts выдаёт бот по правилам дропов.

Полный личный инвентарь подарков Telegram пользователя обычный бот импортировать не может. Mini App показывает подарки, выигранные через &marooow, и каталог подарков, которые бот может отправлять.

## Railway

Start command:

```bash
python -m app.main
```

Variables:

```env
BOT_TOKEN=...
BOT_USERNAME=marooowbot
CHANNEL_ID=-1003791124367
DISCUSSION_CHAT_ID=-1003976665797
ADMIN_IDS=1087968824
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
REDIS_URL=${{Redis.REDIS_URL}}
WEBAPP_ENABLED=true
MINI_APP_URL=https://marooowbot-production.up.railway.app/app

TON_RECEIVER_ADDRESS=UQBbT8RcqxyDMx_Qs0P6Dt-uluyePo10m93rNYF1lXiRM1Zp
TONAPI_KEY=
TON_STARS_PER_TON=170
```

Health check:

```text
https://your-domain.up.railway.app/api/health
```

TonConnect manifest:

```text
https://your-domain.up.railway.app/tonconnect-manifest.json
```

## TON verification

Если `TONAPI_KEY` пустой, TON платеж останется в статусе pending и нужна ручная проверка. Чтобы автозачисление работало, получи ключ TonAPI и укажи `TONAPI_KEY` в Railway.

## BotFather

Web App URL:

```text
https://your-domain.up.railway.app/app
```

Cover: `assets/miniapp_cover_640x360.jpg`.


## Важно про запуск Mini App

Открывать приложение нужно через Telegram WebApp-кнопку, а не обычную ссылку.
В боте есть команда `/miniapp`, она отправляет правильную кнопку `web_app`.
Если открыть просто `https://.../app` в браузере или обычной URL-кнопкой, Telegram initData не передастся и авторизация не сработает.

В Railway переменная должна быть именно с `/app`:

```env
MINI_APP_URL=https://your-domain.up.railway.app/app
WEBAPP_ENABLED=true
```
