# Pace v0.8.2 — Automatic Training sync

This release follows your working Profile and Nutrition sync. It adds Training synchronization while Pace is open and online. You do not need to repeatedly press a sync button: saves trigger a short debounced sync, and Pace also retries on reconnect, app focus and a 30-second interval.

| Component | Version | Patch base |
|---|---|---|
| FastAPI | 0.8.2 | Backend main `84a0acb` — Add Nutrition record synchronization |
| React | 0.16.0 | The complete frontend v0.15 Nutrition-sync source delivered previously |
| Migration | `0009_training_sync` | `0008_nutrition_sync` |

## Included

- Exercise library: custom/starter exercises, favorites, notes and archived exercises.
- Workout templates, exercise order, warm-up and working-set counts, rest preferences and installed-program metadata.
- Training settings, including effort tracking and plate-calculator preferences.
- Completed strength workouts, including all exercise logs, sets, units, weights, reps, durations, effort values and notes.
- Cardio/activity logs, including date, duration, distance and notes.
- Completed Hybrid/HYROX sessions, including ordered splits, distances, reps, loads and timing.
- Offline changes and deletions, duplicate-safe retries, account isolation and explicit conflict choices.

**Active strength and Hybrid sessions stay on their recording device until finished.** Live timers and incomplete set recording are not handed between devices. A completed workout is uploaded as one record together with all its exercises/sets; a Hybrid session includes all its splits. Another device cannot restore half of an uploaded workout.

Training uses a compact automatic-sync status. Its retry button appears only when there is an error. Profile and Nutrition keep their existing controls in this patch. Your requested final design—one automatic sync coordinator and one shared status for the whole app—is recorded in `SYNC_ROADMAP.md`, after Alcohol sync. Alcohol remains local in this release.

## 1. Apply the backend patch

Open Terminal:

```bash
cd /Users/opadigitalmedia/Desktop/pace-backend
git status --short
git log -1 --oneline
```

Commit any of your own outstanding changes before continuing. The patch is based on your backend `main` commit `84a0acb`.

```bash
git switch -c feature/v0.8.2-training-sync
git apply --check ~/Downloads/pace-backend-v0.8.2-training-sync.patch
git apply --index ~/Downloads/pace-backend-v0.8.2-training-sync.patch
```

A successful dry run prints nothing. If it fails, stop before applying and share the error/current commit. Do not force the patch, use `--reject`, or reset your repository to make it fit.

The patch adds a migration and does not change your working `alembic/env.py` or private `.env`.

## 2. Test and commit the backend

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

Expected: **28 passed**. Existing dependency deprecation warnings are non-failing. No new third-party dependency is needed.

If validating migration locally, first ensure your local `.env` points to your local/test database:

```bash
alembic upgrade head
alembic current
```

Expected:

```text
0009_training_sync (head)
```

Then commit the staged patch:

```bash
git diff --cached --stat
git commit -m "Add automatic Training synchronization"
```

## 3. Deploy the backend on Render first

If Render deploys `main`, merge and push through your usual workflow:

```bash
git switch main
git pull --ff-only origin main
git merge feature/v0.8.2-training-sync
git push origin main
```

Use a pull request instead if your repository requires one. Resolve any Git conflicts before finishing the merge.

Keep the existing Render service, database, Supabase URL and CORS settings. If `APP_VERSION` is explicitly configured in Render, change it to `0.8.2`. No new credentials are needed.

Keep your working build command and this startup command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The migration adds `training_sync_records`; existing Profile/Nutrition tables and data remain intact. Each account's existing Training API data is imported on its first Training sync request.

Wait for the migration and Uvicorn startup to complete. Check:

- [API health](https://pace-api-6bb4.onrender.com/health)
- [API documentation](https://pace-api-6bb4.onrender.com/docs)

The docs should include `GET` and `PUT /api/v1/sync/training`. An unauthenticated request should return `401`:

```bash
curl -i https://pace-api-6bb4.onrender.com/api/v1/sync/training
```

Do not bypass migration errors with `alembic stamp`. Fix the deployment before moving to the frontend.

## 4. Apply and test the frontend patch

Open your actual frontend folder:

```bash
cd /path/to/your/pace-frontend
git status --short
git switch -c feature/v0.8.2-training-sync
git apply --check ~/Downloads/pace-frontend-v0.16-training-sync.patch
git apply --index ~/Downloads/pace-frontend-v0.16-training-sync.patch
npm ci
npm test
npm run build
```

Expected: **52 frontend tests pass** and the production build succeeds. The existing large-bundle warning from Vite may appear.

The patch is based on the previous v0.15 Nutrition delivery. If you made additional source changes and the dry run fails, keep them and share the error so the patch can be rebased.

```bash
git diff --cached --stat
git commit -m "Add automatic Training synchronization"
```

The patch files were staged by `git apply --index`; do not add unrelated generated build files to this commit.

## 5. Deploy on Vercel

No environment-variable changes are needed when Nutrition already connects successfully. The API base URL remains:

```dotenv
VITE_API_BASE_URL=https://pace-api-6bb4.onrender.com
```

Keep your working Supabase, feedback and report-problem variables. Do not append `/api/v1` to the base URL.

Merge and push the tested frontend branch:

```bash
git switch main
git pull --ff-only origin main
git merge feature/v0.8.2-training-sync
git push origin main
```

Wait for Vercel to finish. Reopen [Pace](https://pace-beta-omega.vercel.app) and confirm frontend version `0.16.0`. The service-worker cache version is updated.

**Do not clear site storage.** Your original browser contains any Training records that have not yet reached the cloud. Close/reopen old tabs or refresh to update the app.

The source ZIPs are alternative references, without private environment files, installed packages or Git history. Apply the patches to your existing repositories; do not overwrite patched repositories with ZIP contents afterward.

## 6. First automatic sync

1. Open the original browser that holds your Training history.
2. Sign into the account that owns that data.
3. Open Training and wait for **Automatic Training sync · Up to date**.
4. Active sessions stay local; finish them on that device when you normally would. Finishing triggers their upload automatically.
5. Resolve any actual conflicts using the expandable comparison. Choosing a workout version chooses the whole workout, including its sets/splits.

When another device or tab updates Training, Pace shows a reload notice before editing stale screens. Reloading keeps saved local changes but discards unsaved form text. Active recording screens are not disabled by that notice.

Automatic sync requires Pace to be open. If the app is closed or the browser pauses background execution, pending data will be sent after reopening/reconnecting. Render startup delays can cause a timeout; local records and the exact pending request are retained for retry.

## 7. Test on two devices

First let the original device finish importing, then use a second browser or phone with the same account.

### Exercise library, templates and settings

1. Create a custom exercise on A and favorite it.
2. Create a template using it, with warm-up and working sets.
3. Change an effort-mode or plate-calculator setting.
4. Wait for automatic sync, then open/focus Pace on B.
5. Confirm the exercise, favorite, template and settings arrive. Allow up to one periodic sync interval when no focus/reconnect event occurs.

### Strength workout

1. Start the test template on A and log sets, including one weight in `lb` and one effort value.
2. While it is active, verify that B does not gain an active copy. Continue recording on A.
3. Finish the workout on A.
4. After automatic sync, confirm B has the completed workout, correct sets/reps, units, effort values and notes.
5. Reopen/refocus both devices and verify the workout is not duplicated.

### Cardio and Hybrid/HYROX

1. Add a short test run with a distance and note on A. Verify it appears on B.
2. Record and complete a small custom Hybrid session on A. Verify B receives the ordered splits, station loads and times.
3. Compare local history/analytics on both devices after reloading; they read the restored records.

### Offline changes and deletion

1. Use a small completed test workout that already exists on both devices.
2. Disconnect A after Pace has loaded.
3. Delete that test workout and add a Cardio activity while offline.
4. Reload offline if the installed/cached PWA supports it; saved changes should remain.
5. Reconnect A and let automatic sync run.
6. Open/focus B. Confirm the Cardio log arrives once and the deleted workout disappears with its sets.
7. Repeat a sync cycle to confirm the deleted workout does not return.

### Conflict and account isolation

Edit the same Cardio activity differently while both devices are offline. Reconnect A first, then B. B should ask which version to keep. Resolve and verify both devices converge.

Sign into a different Google account and verify that the first account's custom exercises, templates and workout history are absent. Built-in starter exercises are expected for every account.

## Troubleshooting

| Symptom | Action |
|---|---|
| Training endpoint `404` | Deploy the backend patch and confirm the Render branch/commit. |
| Missing table / startup `500` | Confirm `0009_training_sync` ran on the service's configured database. |
| `401` during sync | Sign in again and verify both apps use the same Supabase project. |
| Timeout | Wait for `/health` to respond; Pace retries automatically. Keep local site storage. |
| Validation / `422` | Correct the indicated local record and retry. A definitively rejected batch is cleared so corrected data can be sent; local records remain. |
| Changes waiting | A new template waits for its referenced exercises. Resolve exercise conflicts first. Large imports can take multiple batches. |
| Active workout missing on B | Expected: finish it on its recording device first. |
| `legacy_active_training` | An unfinished session exists in the older backend API. Finish or discard that session through the older API before enabling Training sync. Local active frontend sessions do not trigger this server error. |
| Old Training screen | Use the reload notice or navigate away/back. Keep IndexedDB/site storage. |
| Patch check fails | Share the error and current commit; do not force application. |

Names are limited to 160 characters and notes to 10,000 characters. Uploads contain at most 100 records and 4 MB. A workout can contain up to 100 exercise logs and 200 sets per log. Numeric ranges follow the existing API: non-finite/negative values are rejected, sets allow up to 1,000 reps, Cardio duration up to 48 hours and distance up to 10,000 km. These are validation limits, not training recommendations.

## Data/API compatibility

The server keeps exact frontend documents and their versions in `training_sync_records`. Accepted mutations update the existing relational Training/Cardio/Hybrid tables in the same database transaction. Historical snapshots remain independent of later exercise-library edits.

Existing backend Training records import once per account. Fields absent from the older API, such as secondary-muscle lists and plate inventory, receive frontend defaults during that import. Older arbitrary muscle/equipment labels fall back to `other` where they do not match frontend categories. Legacy pound-based Hybrid loads are converted to kilograms for the frontend. Legacy template-specific targets that the frontend cannot represent remain in their original relational rows until the template is changed; the synced frontend template models set counts rather than per-set target weights/reps. The sync document preserves exact frontend values; some legacy relational fields have narrower precision, such as integer Hybrid distance targets.

After an account enters Training sync, legacy Training/Cardio/Hybrid mutation endpoints return `409 training_sync_required`; writes must use `/api/v1/sync/training`. Read endpoints remain available. This prevents older schemas from silently dropping frontend-only fields. Profile, Nutrition and Alcohol endpoints keep their established behavior.

A conflict is resolved by choosing a whole record. Fields and sets are not silently combined. Receipts retain submitted snapshots for duplicate-safe retries, and deletion markers prevent stale devices from resurrecting removed records. Deleting a visible item does not erase historical receipts.

For this beta, each pull returns the account's full Training sync record set. Pagination/delta cursors, receipt cleanup, full account erasure, closed-app background sync and live-session handoff are outside this release.

## Validation before delivery

- 28 backend tests passed, including existing auth, Profile, Nutrition, Training and Alcohol regressions.
- 52 frontend tests passed, including IndexedDB restoration, immutable retries, deletion, active-session protection and account-specific starter setup.
- Production TypeScript/Vite build passed.
- Isolated SQLite migration upgrade, downgrade and re-upgrade passed; PostgreSQL migration SQL generation passed.
- Both patches applied to clean copies of their exact source bases and produced the expected Git trees.

No production deployment or database mutation was performed for this delivery. Live PostgreSQL concurrency and signed-in browser/device testing remain for your deployed environment. Deploy the backend first, then the frontend. Do not downgrade the production database as a routine frontend rollback.
