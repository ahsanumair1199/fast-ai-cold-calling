# Fast AI Cold Calling

An open-source AI voice cold-calling agent: Twilio places the call, Deepgram
transcribes the caller in real time, an LLM (OpenAI by default) generates the
reply, and ElevenLabs speaks it back — all streamed end to end with barge-in
support so the caller can interrupt the bot mid-sentence.

This is a full rebuild of an earlier prototype, redesigned around three goals:
**concurrency safety** (many simultaneous calls without state bleeding between
them), **low latency** (streaming pipeline, no waiting for full responses),
and **flexibility** (any STT/LLM/TTS vendor can be swapped in behind a thin
interface, without touching the call-handling code).

## Features

- **Real-time voice pipeline** — Twilio Media Streams ↔ Deepgram streaming STT
  ↔ streaming LLM ↔ ElevenLabs streaming TTS, all connected with no
  buffering step in between. Audio stays in mulaw/8000 end-to-end, so there's
  no manual resampling in the hot path.
- **Barge-in / interruption handling** — the caller can start talking while
  the bot is still speaking, and the bot stops immediately instead of
  talking over them.
- **Outbound cold-calling with campaigns** — upload an Excel contact list,
  and the built-in dialer works through it automatically, respecting a
  configurable concurrency cap (`MAX_CONCURRENT_CALLS`), with no duplicate
  dials and no wasted/expired credentials.
- **Per-call isolated state** — every call gets its own session object
  (`CallSession`); there is no shared/global mutable state, so calls placed
  concurrently cannot corrupt each other's conversation, persona, or audio.
- **JWT authentication** with bcrypt-hashed passwords.
- **Per-user configurable voice** — pick an ElevenLabs voice per account.
- **Config-driven persona** — agent name, greeting, role, and company are
  supplied per call/campaign, not hardcoded — the same codebase can run many
  different personas without a code change.
- **Automated test suite** (unit + integration) plus a manual end-to-end
  simulator that replays a real conversation through the live pipeline
  without placing an actual phone call.
- **Docker-ready** — `Dockerfile` and `docker-compose.yml` included (Postgres
  available via a compose profile).

## Built for flexibility

Every external dependency that reasonably has more than one vendor sits
behind a small interface, defined once in `src/core/interfaces.py`:

| Concern | Interface | Current adapter | Location |
|---|---|---|---|
| Speech-to-text | `SttProvider` | Deepgram | `src/providers/stt/deepgram_stt.py` |
| Language model | `LlmProvider` | OpenAI | `src/providers/llm/openai_llm.py` |
| Text-to-speech | `TtsProvider` | ElevenLabs | `src/providers/tts/elevenlabs_tts.py` |

`src/providers/registry.py` is the **only** place that picks a concrete
vendor class based on config — the rest of the app (`src/core/pipeline.py`,
`src/routers/`) only ever depends on the interfaces. Adding a new provider
(Anthropic for the LLM, AssemblyAI for STT, a different TTS vendor, etc.) is:

1. Write one adapter class implementing the relevant interface.
2. Add one line to `registry.py` to construct it.
3. Nothing else changes.

Telephony (Twilio) and the database (SQLAlchemy, SQLite dev / Postgres prod
via `DATABASE_URL`) are the two exceptions — Twilio is wired in directly
since supporting multiple telephony vendors wasn't a near-term goal, and the
DB layer is swappable via connection string alone, no interface needed.

## Is this production-ready?

The core call-handling path is built to production standards:

- No shared mutable state between calls (the root cause of most "works in
  testing, breaks under load" bugs in voice bots).
- Passwords are bcrypt-hashed, phone numbers are validated (E.164) before
  dialing, Twilio webhooks are signature-verified, and CORS is
  environment-aware (locked down outside of `dev`).
- The campaign dialer has a single, idempotent trigger path (Twilio's
  status callback, deduplicated against webhook retries) instead of the
  racy multi-trigger logic common in early prototypes.
- Database migrations are managed with Alembic, not ad hoc table creation.
- Automated tests cover the highest-risk, least-visible-if-broken code: the
  turn-taking/barge-in state machine and the campaign dialer's concurrency
  and idempotency logic.

What you should still do before a real production deployment:

- Rotate `JWT_SECRET_KEY` to a strong random value (`openssl rand -hex 32`)
  and manage all secrets via your platform's secret store, not a committed
  `.env`.
- Add structured logging / tracing / metrics (see [Roadmap](#roadmap)) —
  today's logging is basic.
- Put the app behind HTTPS termination and a process manager / orchestrator
  (Docker Compose is provided as a starting point; see Roadmap for
  Kubernetes).
- Load-test the campaign dialer at your expected concurrent-call volume and
  tune `MAX_CONCURRENT_CALLS` and your Twilio account's concurrency limits
  together.

## Architecture

- **Concurrency-safe by design**: every call gets its own `CallSession` object
  (`src/core/call_session.py`) — no shared/global state, so multiple calls run
  safely in parallel.
- **Pluggable STT / LLM / TTS**: see [Built for flexibility](#built-for-flexibility) above.
- **Low-latency streaming pipeline** (`src/core/pipeline.py`): LLM tokens are
  sentence-chunked and streamed straight into TTS as they arrive — no
  waiting for a full response before speech starts.
- **Campaign dialer** (`src/services/campaign_dialer.py`): polls for pending
  contacts and dials up to `MAX_CONCURRENT_CALLS` at a time, driven solely by
  Twilio's call-status webhook (single source of truth — no duplicate
  triggers, no expiring user tokens).

## Stack

FastAPI · Twilio (telephony) · Deepgram (STT) · OpenAI (LLM) · ElevenLabs (TTS)
· SQLAlchemy async (SQLite for dev, Postgres via `DATABASE_URL` for prod) ·
Redis (webhook↔WebSocket handoff, dialer leader lock) · `uv` for dependencies
· Alembic (migrations) · pytest (tests) · Docker.

## Project structure

```
src/
  main.py                  # FastAPI app factory, startup/shutdown
  config.py                # typed settings, loaded from .env
  db.py                    # async SQLAlchemy engine/session
  redis_client.py          # shared Redis connection pool

  core/
    interfaces.py          # SttProvider / LlmProvider / TtsProvider contracts
    call_session.py        # per-call state (replaces old global variables)
    pipeline.py             # STT -> LLM -> TTS orchestration + barge-in
    barge_in.py              # interrupt/speaking event flags
    session_store.py        # Redis-backed webhook <-> WebSocket handoff

  providers/
    registry.py             # the one place concrete vendors are chosen
    stt/deepgram_stt.py
    llm/openai_llm.py
    tts/elevenlabs_tts.py

  models/                   # SQLAlchemy ORM models
  schemas/                  # Pydantic request/response schemas
  services/                 # business logic (auth, calls, campaigns, dialer)
  routers/                  # FastAPI route handlers
  utils/                    # phone validation, password hashing, Twilio signatures

tests/
  unit/                     # fast, no network (fakes for STT/LLM/TTS)
  integration/               # DB + Redis, mocked Twilio calls
  manual/                    # live end-to-end pipeline test against real APIs
```

## Setup — step by step

### 1. Prerequisites

- **Python 3.12** (a `.python-version` file pins this; `uv` will fetch it
  automatically if it isn't already installed).
- **[uv](https://docs.astral.sh/uv/)** — the project's package/dependency
  manager.
  - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - Or via pip anywhere: `pip install uv`
- **Redis** — used for the webhook↔WebSocket handoff and the campaign
  dialer's leader lock.
  - macOS: `brew install redis && brew services start redis`
  - Linux: `sudo apt install redis-server` (or your distro's equivalent),
    then `sudo systemctl start redis`
  - Windows: install via [Memurai](https://www.memurai.com/) or a Redis
    Windows build, or run it in [WSL](https://learn.microsoft.com/windows/wsl/)
    /Docker (`docker run -p 6379:6379 redis:7-alpine`).
- Accounts + API keys for **Twilio**, **OpenAI**, **ElevenLabs**, and
  **Deepgram** (all have free trial tiers sufficient for development).
- **[ngrok](https://ngrok.com)** (or similar) for local development, so
  Twilio's webhooks can reach your machine over a public HTTPS URL.

### 2. Clone and install dependencies

```bash
git clone <this-repo-url>
cd fast-ai-cold-calling
uv sync
```

`uv sync` creates a `.venv` and installs every dependency pinned in
`uv.lock` — no separate "create a virtualenv" step needed.

### 3. Get your API keys

- **Twilio**: [console.twilio.com](https://console.twilio.com) → copy your
  Account SID, Auth Token, and buy/use a phone number.
- **OpenAI**: [platform.openai.com/api-keys](https://platform.openai.com/account/api-keys)
  → create a new secret key.
- **ElevenLabs**: [elevenlabs.io](https://elevenlabs.io) → profile → API
  key. Also note a voice ID you want to use as the default
  (`api.elevenlabs.io/v1/voices` lists your available voices).
- **Deepgram**: [console.deepgram.com](https://console.deepgram.com) →
  create a project → API key.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` and fill in:

- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`, `ELEVENLABS_DEFAULT_VOICE_ID`
- `DEEPGRAM_API_KEY`
- `JWT_SECRET_KEY` — generate a real one: `openssl rand -hex 32`
  (or, without openssl: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `SERVER_ADDRESS` — your public HTTPS URL (see step 6); Twilio must be able
  to reach this.

`DATABASE_URL` and `REDIS_URL` already have working local defaults (SQLite
file + `localhost:6379`) — only change them if you're pointing at Postgres
or a remote Redis.

### 5. Set up the database

```bash
uv run alembic upgrade head
```

This creates `database.db` (SQLite) with all tables. To use Postgres
instead, set `DATABASE_URL=postgresql+asyncpg://user:pass@host/db` in `.env`
before running this command — the same migrations work against either.

### 6. Expose your local server publicly (for Twilio webhooks)

Twilio needs to reach your machine to deliver call webhooks and stream
audio. In a separate terminal:

```bash
ngrok http 8000
```

Copy the `https://....ngrok-free.app` URL it prints into `SERVER_ADDRESS`
in your `.env`.

### 7. Run the server

```bash
uv run uvicorn src.main:app --reload
```

### 8. Verify it's running

- `GET http://localhost:8000/health` → `{"status": "ok"}`
- `GET http://localhost:8000/docs` → interactive API docs (Swagger UI)

You're now ready to register a user, pick a voice, and place a call via
`POST /calls/outbound` — see [API](#api) below.

## Testing

- `uv run pytest` — unit + integration tests (no live API calls, no phone
  calls placed).
- `uv run python -m tests.manual.generate_fixture` then
  `uv run python -m tests.manual.simulate_call` — replays a recorded
  utterance through the real Deepgram/OpenAI/ElevenLabs pipeline and writes
  the bot's spoken replies to a file, without placing a phone call. Requires
  real API keys in `.env`.
- A real end-to-end phone call requires Twilio + a public `SERVER_ADDRESS`
  (e.g. via ngrok) pointed at `POST /calls/outbound`.

## API

- `POST /auth/register`, `POST /auth/login` — JWT auth.
- `GET/PUT /voices/me` — the caller's ElevenLabs voice.
- `POST /calls/outbound` — place a single ad-hoc call.
- `POST /campaigns` — upload an Excel contact list (`first_name`, `phone`
  columns required) and start a campaign; the dialer works through it
  automatically, respecting `MAX_CONCURRENT_CALLS`.
- `GET /campaigns/{id}/contacts` — check campaign progress.

Full interactive documentation (request/response schemas, try-it-out) is
available at `/docs` once the server is running.

## Roadmap

Ideas for future contributions, roughly in order of likely impact:

- **Inbound call handling** — today the system only places outbound calls;
  answering inbound calls with the same pipeline is a natural extension.
- **Instant filler / "dual prompting"** — speak a tiny (~1-3 word)
  acknowledgment immediately while the real LLM response is still
  generating, shaving a further ~200–400ms off perceived latency.
- **Additional provider adapters** — e.g. Anthropic or an open-weight model
  for the LLM, AssemblyAI or another vendor for STT, a second TTS provider —
  each is a self-contained adapter behind the existing interfaces.
- **Multi-telephony support** — Vonage/Plivo as alternatives to Twilio,
  behind a thin interface (deliberately deferred in this rebuild to keep
  scope tight).
- **Observability** — structured logging, request tracing, and
  Prometheus/Grafana-style metrics (call volume, latency per pipeline
  stage, error rates).
- **Frontend / dashboard** — a UI for managing campaigns, personas, and
  voices, and reviewing call transcripts/recordings.
- **Call recording & transcript storage** — persist full conversations for
  QA and compliance.
- **Rate limiting / abuse protection** on public-facing endpoints.
- **Kubernetes manifests** for horizontally-scaled deployment (the campaign
  dialer's Redis leader lock already makes it safe to run multiple app
  replicas).
- **Payment/billing integration** for a hosted/SaaS offering.
- **CI pipeline** (GitHub Actions) running `pytest` and linting on every PR.

Contributions welcome — open an issue or PR.
