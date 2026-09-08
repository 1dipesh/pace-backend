# Pace Backend

FastAPI and PostgreSQL backend for Pace. Version 0.7 adds authenticated user
identity and keeps all Profile, Nutrition, Strength, Cardio, Hybrid/HYROX, and
Alcohol data scoped to its owning user.

## v0.7 authentication architecture

Pace uses Supabase Auth as its identity provider. The frontend performs Google
or email authentication with Supabase and sends the resulting Supabase access
token to this API:

```http
Authorization: Bearer <supabase-access-token>
```

The backend verifies the JWT signature with the Supabase project's public JWKS,
validates its issuer, audience, expiry, algorithm, subject, and authenticated
role, and then finds or provisions the corresponding `pace_users` row. Passwords,
Google client secrets, refresh tokens, and provider tokens are never stored by
the Pace API.

All feature endpoints are protected. These endpoints remain public:

- `GET /`
- `GET /health`
- `GET /health/database`
- `/docs`, `/redoc`, and `/openapi.json`

`GET /api/v1/auth/me` verifies the current session and returns the linked Pace
user.

## Local setup

Requirements: Python 3.12 and Docker.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API documentation.

## Supabase and Google configuration

1. Create or select the Pace Supabase project.
2. Use an asymmetric JWT signing key for the project so the public JWKS can be
   used for local verification.
3. Enable the Google provider in Supabase Auth.
4. Create a Google OAuth Web client and add the Supabase callback URL shown in
   the provider settings.
5. Add the local and deployed frontend URLs to the Google authorized origins
   and Supabase redirect allow list.
6. Set the backend `SUPABASE_URL` to the project URL. Do not place the Supabase
   service-role key or Google client secret in this backend repository.

Required backend settings:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
AUTH_JWT_ALGORITHMS=["ES256","RS256"]
AUTH_CLOCK_SKEW_SECONDS=30
```

Only include the signing algorithm actually configured for the Supabase project
when deploying to production.

## Frontend request flow

Install `@supabase/supabase-js` in the React application and authenticate there.
After Supabase returns a session, include its access token with Pace API calls:

```ts
const {
  data: { session },
} = await supabase.auth.getSession()

const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
  headers: {
    Authorization: `Bearer ${session?.access_token}`,
  },
})
```

Google sign-in starts in the frontend:

```ts
await supabase.auth.signInWithOAuth({
  provider: "google",
  options: { redirectTo: `${window.location.origin}/auth/callback` },
})
```

Supabase owns registration, email confirmation, password reset, refresh-token
rotation, Google OAuth, and sign-out. Pace owns application data authorization.

## Database migration

Apply migration `0006_authentication`:

```bash
alembic upgrade head
```

Earlier records created through the temporary `dev-local-user` identity remain
attached to that identity and are not silently reassigned. This prevents data
from being claimed by the wrong account. Local-device data migration belongs to
the v0.8 offline-first synchronization milestone.

## Tests

```bash
pytest -q
```

The test configuration uses a temporary SQLite database and a fake token
verifier, so it does not need Supabase credentials or network access. The suite
also directly tests signed JWT verification with an in-memory RSA key.

## Postman

Import:

- `postman/Pace_Local.postman_environment.json`
- `postman/Pace_Backend_v0.7_Authentication.postman_collection.json`

Paste a current Supabase access token into the secret `access_token` environment
variable before running protected requests.
