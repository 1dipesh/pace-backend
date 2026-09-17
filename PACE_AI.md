# Pace AI v0.10 backend

Pace AI is a read-only, account-scoped assistant exposed under `/api/v1/ai`.
It uses OpenAI's Responses API and moderation endpoint. The OpenAI API key is
used only by FastAPI and must never be added to the Vercel frontend.

## Render environment

Add these variables to the Pace API service and redeploy:

```dotenv
OPENAI_API_KEY=your_server_only_api_key
OPENAI_MODEL=gpt-5-mini
AI_BETA_UNLIMITED=true
AI_REQUESTS_PER_MINUTE=10
AI_MAX_INPUT_CHARS=2000
AI_MAX_OUTPUT_TOKENS=700
AI_HISTORY_MESSAGES=20
```

Keep the existing `DATABASE_URL`, Supabase and CORS variables. The normal
Render start command applies migration `0011_ai_chat` before starting FastAPI:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Plans and metering

Every Pace user has an `ai_plan` of `beta`, `free` or `pro`. New and existing
users are assigned `beta`. Beta has no monthly message quota while
`AI_BETA_UNLIMITED=true`; the per-minute abuse limit, input length, bounded
history, moderation and output-token ceiling still apply.

The database records one usage row for each successful or blocked request,
including token counts when OpenAI supplies them. This makes it possible to
activate monthly Free and Pro allowances later without changing the chat
storage schema. Current policy definitions are:

- Beta: unlimited monthly messages during testing
- Free: 30 messages per month when activated
- Pro: 1,000 messages per month when activated

These values are product defaults in `app/services/ai_chat_service.py`, not a
billing system. Payment and subscription verification must be added before a
user can purchase or self-select Pro.

## Safety boundary

- Input and generated output are checked with OpenAI moderation.
- Immediate-danger phrases receive an emergency-services response without an
  AI generation call.
- The system instruction prohibits diagnosis, dangerous alcohol guidance,
  invented facts, disclosure of hidden instructions, and modifying Pace data.
- Pace AI has no tools for logging, changing or deleting nutrition, training,
  alcohol or profile records.
- Responses are plain text in the frontend.
- Conversations are isolated by authenticated Pace user and can be deleted.

These controls reduce risk but cannot guarantee that a model response is
correct. The UI and public Safety page disclose that boundary.

## Endpoints

All endpoints require a valid Supabase bearer token.

- `GET /api/v1/ai/plan`
- `GET /api/v1/ai/conversations`
- `GET /api/v1/ai/conversations/{conversation_id}`
- `POST /api/v1/ai/chat`
- `DELETE /api/v1/ai/conversations/{conversation_id}`

Example message body:

```json
{
  "message": "How should I structure a simple three-day strength week?",
  "conversation_id": null
}
```

## Verification

Run locally without a real API key (the automated tests use a fake provider):

```bash
python -m pip install -e ".[dev]"
pytest -q
```

For a production smoke test, sign in through Pace, open **Pace AI**, send a
low-risk prompt, refresh the page, reopen the conversation and delete it.
Review Render logs for configuration errors without printing the API key.
