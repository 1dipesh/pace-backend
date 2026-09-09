# Pace v0.8 — Profile sync, first delivery

Backend: **0.8.0**. Frontend: **0.14.0** (continues the frontend's independent version numbering).

Patch bases: backend `ad1cd4df3a95b64119bf405319cc62f7602ccc3d`; frontend uploaded source identified by the user as `a655905`.

## What this release does

- Synchronizes the shared Pace profile: date of birth, height, weight, calorie estimate selection, goal, activity level, training experience and days per week.
- Keeps a durable per-account local change state and an immutable pending upload in IndexedDB (schema version 11). Edits made during an upload remain pending afterward.
- Restores a cloud profile when a signed-in device has no local profile.
- Automatically uploads a valid existing local profile when the server has no profile. If both sides differ, asks which saved profile to keep. Matching profiles are reconciled without another upload.
- Uses a mutation UUID and server receipt to replay uncertain requests without writing twice, even when the original response was lost. Receipt storage and the profile update commit together.
- Checks server versions; conflicting edits require a choice. A server deletion is visible as a tombstone and does not silently resurrect from a stale offline edit.
- Checks for changes when the signed-in app opens, returns to focus, reconnects, saves a profile, or the user selects Sync now. While mounted, it also checks every 30 seconds. This is foreground synchronization, not background sync after the app is closed.
- Limits each API fetch to 15 seconds. If Render is asleep, local data remains available and a later attempt can succeed.
- Keeps API responses outside the PWA cache. A new shell cache version ships with this release.

**Nutrition targets, food logs, strength workouts, cardio/HYROX, Alcohol records and the separate Alcohol profile do not sync in this delivery.** They remain local. Importing these records is a later v0.8 stage. Profile sync does not automatically apply Nutrition recommendations or change the separate Alcohol profile on another device.

Older profiles containing only age require the user to enter a real date of birth before upload. No birth date is fabricated.

## 1. Apply the backend patch locally

Open your backend repository. The tree should be clean before proceeding. If you have unrelated changes, preserve them separately first.

```bash
cd /Users/opadigitalmedia/Desktop/pace-backend
git switch main
git pull --ff-only origin main
git status --short
git rev-parse --short HEAD
git switch -c feature/v0.8-profile-sync
git apply --check ~/Downloads/pace-backend-v0.8-profile-sync.patch
git apply --index ~/Downloads/pace-backend-v0.8-profile-sync.patch
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

Expected suite: **16 passed**. If `git apply --check` fails, stop and send the output; do not force partial application.

If `.env` contains `APP_VERSION=0.7.0`, change it locally to `APP_VERSION=0.8.0`. Do not commit `.env`.

Review and commit:

```bash
git diff --cached --stat
git commit -m "Add v0.8 profile synchronization"
git push -u origin feature/v0.8-profile-sync
```

## 2. Apply the frontend patch locally

Open your actual frontend repository folder (adjust the example path if needed).

```bash
cd /Users/opadigitalmedia/Desktop/pace
git switch main
git pull --ff-only origin main
git status --short
git rev-parse --short HEAD
git switch -c feature/v0.8-profile-sync
git apply --check ~/Downloads/pace-frontend-v0.14-profile-sync.patch
git apply --index ~/Downloads/pace-frontend-v0.14-profile-sync.patch
npm ci
npm test
npm run build
```

Expected suite: **23 passed**. The existing large-bundle warning is non-fatal. Build output may change tracked `.tsbuildinfo` files from the original project; they are not part of this patch, so do not add them to the commit.

```bash
git diff --cached --stat
git commit -m "Add offline profile synchronization"
git push -u origin feature/v0.8-profile-sync
```

## 3. Deploy the backend FIRST

After local checks, merge the backend branch into its main branch (or merge its GitHub PR):

```bash
cd /Users/opadigitalmedia/Desktop/pace-backend
git switch main
git pull --ff-only origin main
git merge feature/v0.8-profile-sync
git push origin main
```

Render should deploy the new commit. Keep its current start command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set Render's `APP_VERSION` to `0.8.0`. Keep the existing `DATABASE_URL`, Supabase settings, ES256 algorithm and CORS origin. No new secret is required.

Keep the Supabase **Data API disabled** for this FastAPI-only data architecture. The new receipt table includes profile snapshots and must not be exposed through an alternative unauthenticated data path. Supabase Auth remains enabled.

The migration creates `pace_sync_receipts`; it does not copy your local PostgreSQL database, erase existing profiles or touch other module tables. In Supabase SQL Editor:

```sql
SELECT version_num FROM public.alembic_version;
```

Expected: `0007_profile_sync`.

Check these URLs after Render is live:

- https://pace-api-6bb4.onrender.com/health
- https://pace-api-6bb4.onrender.com/health/database
- https://pace-api-6bb4.onrender.com/docs

Both health checks should return 200. Swagger should list GET and PUT `/api/v1/sync/profile`. An unauthenticated request to the sync endpoint should return 401.

## 4. Deploy the frontend

Only after the backend is healthy, merge the frontend branch into its main branch or merge its PR:

```bash
cd /Users/opadigitalmedia/Desktop/pace
git switch main
git pull --ff-only origin main
git merge feature/v0.8-profile-sync
git push origin main
```

Vercel should deploy. Keep:

```dotenv
VITE_API_BASE_URL=https://pace-api-6bb4.onrender.com
```

Keep the existing Supabase URL and publishable key. No OAuth callback change is needed. Open https://pace-beta-omega.vercel.app and reload when the new deployment is ready. Close older Pace tabs if the IndexedDB upgrade is blocked. **Do not clear site data**: activity records are not backed up by this release.

## 5. Test in this order

1. On your existing device, sign in and open Profile. A new Profile sync card should appear. If your stored profile lacks DOB, add it and save.
2. Wait for Synced. If both local and cloud profiles already exist and differ, inspect the displayed values before choosing. This may upload your local shared profile for the first time.
3. In Supabase, confirm your row in `pace_profiles` has the expected values and version. Do not publish your DOB or database credentials when sharing results.
4. Sign into the same account in a new browser/private window or phone. The shared profile should restore; the other modules will still have device-local data.
5. On device A, disconnect the network while the page remains open, change weight and save. Expect Changes pending. Reconnect and expect Synced. On device B, select Sync now; if the form was already open, choose Reload saved profile to display the restored values. Reload discards unsaved form edits.
6. Test conflict handling: first sync both devices to the same profile. Disconnect A, edit and save there. Edit and sync a different profile on B. Reconnect A. It should show Needs your choice. Choose the intended saved version; it must not silently overwrite B.
7. Sign out and sign into a second account in the same browser. It must not receive the first account's profile or pending uploads.
8. Stop local FastAPI and Cloudflare Tunnel. Repeat an online profile save to confirm traffic goes to Render.

A profile form refreshed by cloud changes stops accepting saves until you reload it. This prevents an old open form from silently replacing newer cloud data. Pending uploads survive page reloads; retries use the same mutation ID.

## Verification performed for this delivery

- Backend: 16 passing tests, including protected sync routes, idempotent retries, reused-ID rejection, stale-version conflict, account isolation, deletion/restore and invalid input rejection.
- Frontend: 23 passing tests, including mapping, legacy DOB handling, new-device restoration, lost-response replay, edits during upload, cancellation after account switch, tombstones, and durable/atomic IndexedDB storage.
- TypeScript/Vite production build passes.
- Migration upgraded, downgraded to 0006, and upgraded again on a temporary SQLite database. PostgreSQL migration SQL generation also verified.
- Patch application checked against clean copies of both source bases.

Limitations: no changes were pushed or deployed to your accounts. Live Google-authenticated cross-device testing remains to be performed using the steps above. Browser automation could not run because the Chromium download timed out. PostgreSQL row-lock concurrency was not exercised against a live PostgreSQL test instance; migration execution was tested with SQLite, with PostgreSQL SQL generation checked separately.

## Rollback and retention

Prefer fixing forward. If the frontend rollout needs to be stopped, use Vercel's previous deployment; leave migration 0007 and its receipts in place. Never clear IndexedDB to roll back, and do not delete receipts while devices may still replay queued uploads.

The receipt table retains successful profile snapshots for deduplication. It is account-scoped and cascades on deletion of the owning Pace user. This release adds no receipt-cleanup job or account-deletion UI; retention and deletion workflows remain work before broader public release.

## Next stage

Once the online tests pass, extend the foundation to Nutrition. That requires relationships and stable IDs for foods, meals, entries and goals; it is not achieved by simply switching those repositories to HTTP.
