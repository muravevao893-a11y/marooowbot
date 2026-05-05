# &marooow giveaway bot

Telegram-бот для канала/чата с авто-дропами, шансами за комментарии, рефералкой и красивым HTML-оформлением сообщений.

## Что есть в этой версии

- авто-сообщение под каждым новым постом канала;
- шанс выпадения мишки за комментарий;
- победа ответом на комментарий + кнопка «Забрать подарок»;
- админы/основатель не участвуют;
- реферальная система: активный реферал = +0.1% к шансу;
- защита рефов: 5 комментариев под 2 разными постами + подписка;
- антиспам: cooldown, лимит попыток в час, фильтр коротких/одинаковых комментариев;
- `/chance` — личный шанс пользователя;
- `/winners` — последние победители;
- `/refs` — топ активных рефералов;
- `/activity` — топ активности за неделю;
- `/stats` — админская статистика;
- автопруф в канал после успешной выдачи подарка;
- ручные розыгрыши через `/admin`;
- Stars: `/balance`, `/topup 100`, `/gifts`;
- PostgreSQL + Redis + Railway-ready структура.

## Railway variables

Обязательно укажи в service с ботом:

```env
BOT_TOKEN=...
BOT_USERNAME=marooowbot
ADMIN_IDS=твой_telegram_id
CHANNEL_ID=-100...
DISCUSSION_CHAT_ID=-100...
DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
REDIS_URL=${{Redis.REDIS_URL}}
```

Важно: у `CHANNEL_ID` и `DISCUSSION_CHAT_ID` должен быть один минус перед `100`.

## Start command

```bash
python -m app.main
```

## Как взять AUTO_DROP_GIFT_ID

В личке бота, от админа:

```text
/gifts
```

Скопируй ID нужного подарка и поставь в Railway:

```env
AUTO_DROP_GIFT_ID=...
```

## Как пополнить Stars

```text
/topup 100
/balance
```

## Команды пользователя

```text
/start
/profile
/chance
/winners
/refs
/activity
/rules
```

## Команды админа

```text
/admin
/stats
/gifts
/balance
/topup 100
```

## Рефералка

В профиле у каждого пользователя будет ссылка:

```text
https://t.me/marooowbot?start=ref_USER_ID
```

Реф засчитывается, когда приглашённый:

1. нажал `/start` по ссылке;
2. подписан на канал;
3. написал 5 комментариев;
4. комментарии были под 2 разными постами;
5. не админ и не забанен.

Каждый активный реф даёт +0.1% к шансу, максимум +3%.
