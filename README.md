# Neura — Telegram AI Bot (Webhook, Railway-ready)

Python 3.13, FastAPI webhook server, python-telegram-bot v21, Supabase history
storage keyed on `(user_id, group_id)`, talks to an OpenAI-compatible LLM
endpoint (e.g. your LiteLLM proxy at `api.neam.top`).

## 1. Supabase setup

1. Create a Supabase project.
2. Open the SQL editor and run `schema.sql` from this repo.
3. Grab your project URL and **service role key** (Settings → API).

## 2. Telegram bot

1. Talk to @BotFather, create a bot, copy the token.
2. If you also want inline mode (`@yourbot query`), run `/setinline` in
   BotFather and set a placeholder text.

## 3. Local env

```bash
cp .env.example .env
# fill in BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY, LLM_API_BASE, LLM_API_KEY
```

`WEBHOOK_URL` should be left for the Railway domain once deployed — you don't
need it for purely local testing since webhooks require a public HTTPS URL
anyway (use a tunnel if you want to test locally before deploying).

## 4. Deploy to Railway

1. Push this folder to a GitHub repo.
2. Railway → New Project → Deploy from GitHub repo.
3. Railway auto-detects Python via `runtime.txt` and `requirements.txt`.
4. In the service Settings, confirm the start command is picked up from
   `railway.json`:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Add environment variables in the Railway dashboard (Variables tab):
   ```
   BOT_TOKEN
   SUPABASE_URL
   SUPABASE_KEY
   LLM_API_BASE
   LLM_API_KEY
   LLM_MODEL        (optional, defaults to deepseek-v4)
   HISTORY_LIMIT     (optional, defaults to 10)
   WEBHOOK_URL
   ```
6. Deploy. Railway gives you a `*.up.railway.app` domain — set that as
   `WEBHOOK_URL` (include `https://`, no trailing slash), then redeploy so
   the env var takes effect.

The app registers the Telegram webhook automatically on every startup
(`lifespan` in `main.py`), so you never need to call `setWebhook` by hand —
redeploys self-heal the webhook URL.

## 5. Custom domain (optional)

Railway → Service → Settings → Networking → Custom Domain → add e.g.
`bot.neam.top` → copy the CNAME target → add that CNAME record in your
Cloudflare DNS for `neam.top`. Once it resolves, update `WEBHOOK_URL` to the
custom domain and redeploy.

## 6. Verify

```bash
curl https://your-domain/
# {"status": "alive"}
```

Message the bot in DM or mention it in a group — it should reply using
DeepSeek (or whatever `LLM_MODEL` you set) through your LiteLLM proxy.

## Notes

- History is scoped strictly to `(user_id, group_id)` — the same person in
  two different groups has fully separate conversations.
- Inline mode (`@yourbot query`) does **not** have access to `group_id`
  (Telegram limitation), so inline replies are stateless and don't read/write
  group history. See `bot/ai.py:generate_inline_reply`.
- `HISTORY_LIMIT` controls how many prior turns get sent to the LLM per
  request — raise it for more context, lower it to cut token cost.
