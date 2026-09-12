# Pace Alcohol sync — deployment and testing

Backend v0.8.3 · Frontend v0.17.0

This release adds automatic synchronization for completed Alcohol sessions (drinks, water and breaks), favorites, and the Alcohol eligibility/weight/onboarding profile. It builds on the working Training sync release. Deploy the backend first, then the frontend.

## What changes

- GET and PUT `/api/v1/sync/alcohol`, protected with the existing Supabase access token.
- A session and all its children upload and restore atomically.
- Stable record IDs, expected versions, durable retry receipts and deletion markers.
- Concurrent changes require an explicit choice; they are not silently overwritten.
- Favorites and Alcohol profile sync independently of session histories.
- Local Alcohol profile moves from account-specific localStorage into IndexedDB, with a one-time import. General Pace profile and Alcohol eligibility remain separate.
- Atomic local deletion, backdated-session creation and favorite quick-add.
- Automatic sync on saved changes, opening Pace, regaining focus, reconnection and a periodic retry while Pace is open. Routine manual syncing is unnecessary.
- A compact Alcohol status and conflict/retry controls. The single shared coordinator and removal of existing module cards are the next milestone.

Active and paused sessions stay on their recording device until explicitly ended. A reopened session stays local until ended again; its earlier completed cloud copy may remain visible on other devices. If that copy is edited elsewhere, the completed session will require conflict resolution. This release does not transfer active sessions between devices. Alcohol profile sync waits during an active Alcohol session so incoming weight/eligibility changes do not change its estimate inputs. Browser notification permission stays device-specific.

## 1. Prepare the backend repository

Open Terminal in your existing backend repository. These commands assume the patch was downloaded to `~/Downloads`.

```bash
git status --short
git log -1 --oneline
git switch -c feature/v0.8.3-alcohol-sync
git apply --check ~/Downloads/pace-backend-v0.8.3-alcohol-sync.patch
git apply --index ~/Downloads/pace-backend-v0.8.3-alcohol-sync.patch
git diff --cached --stat
```

Start with a clean working tree. The patch was built against backend Training-sync commit `49cc82b36914a5151a0c0b3474a2ce48ab85ab64`. Your commit hash can differ if you applied the prior patch and committed it yourself; the relevant check is whether `git apply --check` succeeds. If it fails, do not force the patch or choose one side of a merge blindly. Preserve your changes and provide the current source for reconciliation.

Activate your existing virtual environment and run:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

Expected: **35 passed**. The tests use a temporary SQLite database and test authentication identities, not your production account.

For a local development database, apply the migration:

```bash
alembic upgrade head
alembic current
```

Expected migration: `0010_alcohol_sync (head)`.

This migration adds `alcohol_sync_records`; it does not drop your existing Alcohol tables or records. Existing REST-created records are imported for each authenticated account on its first Alcohol sync request. Old REST writes are then blocked for that account, because they cannot maintain the new versioned sync documents. Existing REST reads remain available.

## 2. Commit and deploy the backend to Render

```bash
git commit -m "Add automatic Alcohol synchronization"
git push -u origin feature/v0.8.3-alcohol-sync
```

Merge this branch into the branch your Render service deploys (currently `main` in your setup). In Render, wait for the new deployment to become live. If automatic deployment is disabled, deploy the latest commit manually.

Keep the current database connection, Supabase and CORS settings. No new credentials are required. If you have an explicit `APP_VERSION` variable in Render, change it to `0.8.3`.

Your existing start command should continue to apply migrations before starting FastAPI:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Check the Render log for the upgrade from `0009_training_sync` to `0010_alcohol_sync` and successful server startup. Open:

- https://pace-api-6bb4.onrender.com/health
- https://pace-api-6bb4.onrender.com/docs

The docs should show GET and PUT `/api/v1/sync/alcohol`.

An unauthenticated request is expected to return **401**, not 200:

```bash
curl -i https://pace-api-6bb4.onrender.com/api/v1/sync/alcohol
```

A health response alone does not verify authenticated synchronization; complete the two-device checks below.

## 3. Apply the frontend patch

Open a separate terminal in your frontend repository:

```bash
git status --short
git switch -c feature/v0.17-alcohol-sync
git apply --check ~/Downloads/pace-frontend-v0.17-alcohol-sync.patch
git apply --index ~/Downloads/pace-frontend-v0.17-alcohol-sync.patch
npm ci
npm test
npm run build
```

Expected: **66 tests passed** and a successful production build. The existing large JavaScript chunk warning is non-failing; bundle splitting remains future optimization work.

The patch base is frontend Training-sync commit `08d594a4f05e270d3492602987f8faf92b2816e8`. As with the backend, equivalent source with a different commit hash is acceptable if the patch check succeeds.

IndexedDB upgrades from version 11 to 12 and adds an Alcohol profile store. Existing sessions and other module data are preserved. Close other Pace tabs if a database upgrade is blocked. Do not clear browser data to resolve an upgrade issue: it may contain unsent history.

## 4. Commit and deploy the frontend to Vercel

```bash
git commit -m "Add automatic Alcohol synchronization"
git push -u origin feature/v0.17-alcohol-sync
```

Merge into the frontend production branch and wait for Vercel to finish deploying. Keep your existing Supabase variables and:

```dotenv
VITE_API_BASE_URL=https://pace-api-6bb4.onrender.com
```

Do not append `/api/v1`. No new environment variables are needed.

Open https://pace-beta-omega.vercel.app using the browser that currently contains your Alcohol history. Sign in with its owning account. If an installed PWA shows the old version, close and reopen it, then reload; do not delete its site data. The app version should show `0.17.0`.

## 5. Test normal synchronization on two devices

Use the same Google account on both devices. The new release automatically uploads completed history from the original browser; it cannot upload records from a browser that has not opened the new release.

1. On device A, open Alcohol and wait for the automatic sync status to finish.
2. On device B, open Pace and sign in with the same account.
3. Verify completed session dates, drinks, quantities, ABV, water entries, breaks and favorites.
4. Add a backdated session on A with two drinks. Wait for synchronization.
5. Refocus/reopen Pace on B and verify the new session has both drinks.
6. Edit a drink or favorite on A; verify the change on B.
7. Delete a test completed session on A; verify it disappears on B, including after reopening B.

When Pace reports that records changed in another tab/device, reload before editing. This prevents an already-open form from replacing newer records with stale field values. The reload notice explains that unsaved form text will be discarded.

## 6. Test active sessions and offline use

1. Start a live session on A and log a drink, water and a break.
2. Confirm that the active session remains on A. It should not become an active session on B.
3. End it explicitly on A. After sync, verify the full completed session on B.
4. Disconnect A from the internet. Add a backdated session or edit a favorite.
5. Verify the change survives a reload on A, assuming the PWA shell has already been cached.
6. Reconnect and wait for automatic synchronization. Verify the change on B.

Do not uninstall or clear storage while records are waiting to upload. Closing Pace stops its normal browser-driven sync until it is opened again.

## 7. Test conflicts and account isolation

Use a disposable test session or favorite.

1. Let both devices receive the same version.
2. Take A offline and edit it.
3. Edit the same record on B and let B finish syncing.
4. Reconnect A. Pace should ask which version to keep.
5. Review the displayed versions, choose one, and verify both devices eventually show it.

For a session, the choice covers the whole session, including drinks, water and breaks. Independent records can continue syncing while that conflict awaits a decision.

Sign out and sign in with another Google account. That account must not see the first account's Alcohol history. Sign back into the original account to restore its view.

## Troubleshooting

- **404 on sync:** the backend deployment is older than v0.8.3. Deploy it first.
- **401:** sign in again and confirm backend and frontend use the same Supabase project.
- **500 / missing relation:** check Render logs and confirm migration `0010_alcohol_sync` ran successfully.
- **`legacy_active_alcohol`:** an active session was created through the older REST API. Complete it via that API's `/api/v1/alcohol/sessions/{id}/complete` action, or explicitly discard it there, then retry. A locally active PWA session does not cause this bootstrap error.
- **422:** a record failed validation or has an ID collision. Local data is preserved. Report the error without sharing an access token; do not clear storage.
- **Taking too long:** the client retains its pending batch and retries. If it persists, inspect Render logs and the API connection.
- **Profile waiting during an active session:** intentional. Finish the session to resume Alcohol profile synchronization.
- **New browser has no history:** first open the original browser with the new version and let its completed records upload.

## Validation and limits

Verified locally: 35 backend tests, 66 frontend tests, TypeScript/Vite production build, SQLite migration upgrade/downgrade/upgrade, and patch application against both exact bases. PostgreSQL migration SQL is compiled separately. The live Render/Supabase database is not modified or tested by this delivery; complete the production checks above after deployment.

The API currently returns the account's full Alcohol history. Batches are limited to 100 documents / 4 MB, with at most 2,000 children of each kind per session; the frontend leaves oversized records local with a visible error. Incremental sync/pagination and retention policies are later hardening work. Retry receipts retain historical snapshots, including records deleted from the normal UI; visible deletion is not yet a complete account erasure feature.

Do not downgrade production migrations after syncing real data: deleting sync metadata can lose retry/version history and the cloud Alcohol profile. Fix forward and preserve backups. The included full-source archives are alternatives for inspection/recovery; do not overwrite a configured working repository with them or apply the patch a second time.

Next milestone: one shared automatic-sync coordinator and compact status for Profile, Nutrition, Training and Alcohol, with a single retry action when needed.
