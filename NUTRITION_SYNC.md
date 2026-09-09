# Pace v0.8.1 — Nutrition synchronization

This release adds Nutrition sync after the working v0.8 profile sync.

| Component | New version | Patch base |
|---|---|---|
| FastAPI backend | 0.8.1 | Backend `main` commit `4eb4d0d` (working profile sync) |
| React frontend | 0.15.0 | Exact contents of your uploaded `pace-frontend-current(1).zip` |
| Database migration | `0008_nutrition_sync` | `0007_profile_sync` |

The frontend and backend use separate version numbers. Frontend 0.15.0 implements the Nutrition portion of the backend v0.8 synchronization milestone.

## What now syncs

- Food library: starter and custom foods, favorites, usage information, preparation, serving labels and notes.
- One-off foods used by diary entries, without adding them to the visible food library.
- Saved meals and their ordered ingredients.
- Daily entries: date, amount, stored nutrient values, food descriptions and meal grouping.
- Nutrition targets, including records with only some targets configured.
- Deleted entries and saved meals, using server deletion markers.

Existing local records upload with stable IDs. Repeating an upload does not create additional foods, meals or entries. Changing a food's nutrient values does not recalculate old diary entries. Editing an entry's amount still recalculates that entry as it did before this release.

Profile sync continues separately. Training, Cardio, Hybrid/HYROX and Alcohol data remain local; those are later milestones.

**Keep the browser that contains your existing data. Do not clear its site storage.** Deploy both patches, then let that browser finish its first Nutrition sync before testing a second device. Different browsers have separate local databases, even on the same computer.

## 1. Apply the backend patch

In Terminal, open your backend repository:

```bash
cd /Users/opadigitalmedia/Desktop/pace-backend
git status --short
git log -1 --oneline
```

The working tree should be clean. Commit your own outstanding changes before continuing. The supplied backend patch was built against `4eb4d0d`; a later compatible commit may also work, but the dry run below is the deciding check.

Create a branch and check the patch:

```bash
git switch -c feature/v0.8.1-nutrition-sync
git apply --check ~/Downloads/pace-backend-v0.8.1-nutrition-sync.patch
```

No output from `git apply --check` means the patch fits. Apply and stage it:

```bash
git apply --index ~/Downloads/pace-backend-v0.8.1-nutrition-sync.patch
git diff --cached --stat
```

This patch adds a migration; it does not modify your working `alembic/env.py` or your private `.env`.

If the dry run fails, stop before applying. Send the error and your current commit. Do not use `--reject`, replace `env.py`, or reset your branch to make it fit.

## 2. Validate the backend locally

Activate your existing virtual environment and install the project:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

Expected result: **22 passed**. No new third-party backend dependency is required. Two existing dependency deprecation warnings may appear.

For local migration validation, make sure your local `.env` points to your local/test PostgreSQL database. Then:

```bash
alembic upgrade head
alembic current
```

Expected head:

```text
0008_nutrition_sync (head)
```

The migration adds `nutrition_sync_records`. It does not remove or rewrite your existing profile, Nutrition, Training or Alcohol tables. Existing Nutrition API records are imported for each account on that account's first sync request, not during the schema migration.

Commit the staged patch:

```bash
git commit -m "Add Nutrition record synchronization"
```

If tests produced unrelated generated files, leave those out of this commit. The patch's changes were already staged by `git apply --index`.

## 3. Deploy the backend on Render first

If Render deploys your `main` branch, merge your tested feature branch into `main` and push:

```bash
git switch main
git pull --ff-only origin main
git merge feature/v0.8.1-nutrition-sync
git push origin main
```

If your repository requires a pull request, use that workflow to merge instead. If Git reports a conflict, resolve it before committing the merge; do not push an unfinished merge.

In your existing Render service for `pace-api-6bb4`, keep the working database, Supabase and CORS settings. No new credentials are needed. If you explicitly set `APP_VERSION`, update it to `0.8.1`.

Keep your existing working build command. Your startup command should still run migrations before Uvicorn:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Watch the deployment log. The migration should finish, then Uvicorn should start. Do not run `alembic stamp head` to bypass a migration error.

Verify:

- [API health](https://pace-api-6bb4.onrender.com/health)
- [API documentation](https://pace-api-6bb4.onrender.com/docs)

The documentation should include `GET` and `PUT /api/v1/sync/nutrition`. Opening the protected endpoint without a token should return `401`, which confirms protection rather than a deployment failure:

```bash
curl -i https://pace-api-6bb4.onrender.com/api/v1/sync/nutrition
```

Do not continue to the frontend deployment if the backend migration or startup is failing.

## 4. Apply the frontend patch

Open the frontend repository in Terminal. Replace the path below with your actual frontend folder:

```bash
cd /path/to/your/pace-frontend
git status --short
git switch -c feature/v0.8.1-nutrition-sync
git apply --check ~/Downloads/pace-frontend-v0.15-nutrition-sync.patch
git apply --index ~/Downloads/pace-frontend-v0.15-nutrition-sync.patch
npm ci
npm test
npm run build
```

Expected: **39 tests pass** and the production build completes. Vite may report the existing large-bundle warning; it is not a build failure.

The patch preserves the working profile-sync code and uses the existing IndexedDB `syncState` store. No browser storage reset or IndexedDB schema upgrade is required.

Commit:

```bash
git commit -m "Add offline Nutrition synchronization"
```

The complete source ZIPs are alternative references. Do not apply the patch and then overwrite your repository with the ZIP. Source ZIPs do not include `.env`, installed dependencies or Git history.

## 5. Deploy the frontend on Vercel

Keep your existing working frontend variables:

```dotenv
VITE_API_BASE_URL=https://pace-api-6bb4.onrender.com
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_EXISTING_PUBLISHABLE_KEY
```

Do not add `/api/v1` to the API base URL. No variable needs to change if profile sync already uses this backend. Keep your feedback/report URLs as they are.

Merge and push the tested frontend branch through your usual workflow:

```bash
git switch main
git pull --ff-only origin main
git merge feature/v0.8.1-nutrition-sync
git push origin main
```

Wait for the new Vercel deployment to become ready. Close old Pace tabs and reopen [Pace](https://pace-beta-omega.vercel.app). Refresh if necessary so the new service worker and app load. **Do not clear site data to update the app.**

Frontend version should now show `0.15.0`.

## 6. First sync on your original device

1. Sign in with the account that owns your current local records.
2. Open Nutrition or your Pace account/profile page.
3. Find the **Nutrition sync** card.
4. Press **Sync Nutrition now**, and wait for **Up to date** with a last-synced time.
5. If there are conflicts, expand **Compare versions**. Choose **Keep this device’s version** or **Use cloud version** for each record. The chosen version replaces the other; fields are not automatically combined.
6. If Pace reports that Nutrition was updated from another device, use **Reload Nutrition** before editing. Saved offline changes remain in storage. Unsaved form text is discarded on reload.

Pace sends at most 200 records per upload. Foods upload before new meal/entry references. Larger initial histories can require several batches. A missing or conflicted food can leave a dependent meal or entry waiting until the food is resolved.

If Render takes too long to respond, records remain local and Pace retries. A first timeout is not evidence that data has been lost. Retry after the API is responsive.

## 7. Online verification on two devices

On device A:

1. Create a custom food named `Sync test oats`.
2. Favorite it.
3. Create a saved meal containing that food.
4. Log the meal to today's diary.
5. Set or change a Nutrition target.
6. Wait for Nutrition to show **Up to date**.

On device B, open Pace in another browser or on your phone and sign into the **same** account:

1. Confirm the custom food and favorite appear.
2. Confirm the saved meal contains the correct food and amount.
3. Confirm today's diary entries appear with the correct meal grouping and nutrient totals.
4. Confirm the Nutrition target matches.
5. Sync twice more and verify there are no additional copies.

Change the custom food's calories on device B and sync. Return to A, sync and reload when prompted. The food should update while the already-logged diary entry retains its historical calories.

## 8. Offline and deletion verification

Use a small test entry for this check:

1. On A, create a test entry and let it sync.
2. Disconnect A from the internet after Pace is loaded.
3. Add another test entry, edit a saved meal and delete the first synced test entry.
4. Reload A while offline if the PWA is installed/cached. The saved local changes should remain.
5. Reconnect and press **Sync Nutrition now**.
6. On B, sync and reload when prompted.
7. Confirm the new entry appears once, the meal edit arrives and the deleted entry stays deleted.
8. Sync again on A and B. The deletion should not reappear.

For a conflict test, first sync a custom food on both devices. Take both offline, edit that same food differently on each device, then reconnect A followed by B. B should offer a choice instead of silently replacing A's edit. Resolve the conflict and confirm both devices converge.

Finally, sign into a different Google account. It should not see the first account's custom test foods, meals, entries or goals. Built-in starter foods are expected to appear for each account.

## Troubleshooting

| Result | What to do |
|---|---|
| Nutrition endpoint `404` | Deploy the backend patch and confirm Render deployed the expected branch/commit. |
| `401` while signed in | Sign out/in to refresh the session; verify the backend and frontend still use the same Supabase project. |
| Missing `nutrition_sync_records` table / API `500` | Check that `alembic upgrade head` completed against the Render service's configured database. |
| API timeout | Open `/health`, wait for the service to respond, then retry. Keep browser storage. |
| CORS/network error | Preserve the working CORS origin `https://pace-beta-omega.vercel.app` and check the frontend's API base URL. |
| Validation / `422` | A record exceeds the supported schema or lacks a food reference. Correct that record and retry. Local records are retained; a rejected batch is cleared so a correction can be submitted. Share the error and record name if it persists, without access tokens. |
| Changes waiting | Resolve any food conflicts first. Ensure meals reference available foods. A large import may need another sync pass. |
| Old page after sync | Use the reload notice or close/reopen Pace. Do not clear IndexedDB/site data. |
| `git apply --check` fails | Share the error and current commit. Keep the repository unchanged until the patch is rebased. |

Names/labels are limited to 160 characters, notes to 4,000 characters, meals to 200 ingredients, and food/entry amounts to 0.01–100,000 units. Nutrient and target limits follow the existing API's practical ranges. Non-finite and negative values are rejected. A validation error never deletes the local record.

## Backend compatibility and data handling

The sync API stores each account's exact frontend records, versions and deletion markers in `nutrition_sync_records`, and updates the existing relational Nutrition tables in the same transaction. Those tables continue to support existing read endpoints and daily summaries. Hidden fields such as meal grouping, free-text preparation and serving labels remain exact in sync records.

Optional target records that omit calories/protein/carbs/fat are preserved by the sync API. The older goals endpoint requires all four targets, so it exposes a goals row only once they are complete.

On the first sync request, existing Nutrition REST records are imported with their existing IDs. Manual diary snapshots receive hidden food records for the frontend's edit/repeat actions. A deleted food still referenced by a legacy diary entry or meal is preserved as a hidden archival food; the original food keeps its deletion marker.

After an account enters Nutrition sync, legacy Nutrition `POST`, `PUT`, `PATCH` and `DELETE` routes return `409 nutrition_sync_required`. Use `/api/v1/sync/nutrition` for writes. This avoids a second write path silently discarding fields that the older API does not understand. Legacy reads remain available. Other modules' APIs are unaffected.

Conflicts use server versions rather than client clocks. Each upload has a durable mutation ID and an atomic server receipt. Account locks serialize Nutrition writers on PostgreSQL. The client saves its exact pending request before sending it and finishes that request after a restart or lost response. Acknowledgements advance the merge base without overwriting edits made during the request.

For this beta, each pull retrieves the account's full Nutrition record set, including deletion markers. This is not yet a paginated delta-sync protocol for very large histories. Upload receipts retain submitted snapshots for retry safety; deleting a visible record does not erase historical receipts. Training and Alcohol synchronization, receipt-retention tooling and full account-data erasure are outside this release.

## Verification performed before delivery

- 22 backend tests passed, including existing API/auth/profile regression tests.
- 39 frontend tests passed, including real IndexedDB behavior through `fake-indexeddb`.
- Production TypeScript/Vite build completed.
- Migration upgrade, downgrade to `0007_profile_sync`, and re-upgrade passed on an isolated SQLite database.
- PostgreSQL migration SQL generation passed.
- Both patches were checked and applied to clean copies of their exact source bases; resulting Git trees matched the delivered commits.

No production database was changed and no deployment was triggered by this work. Live PostgreSQL concurrency and signed-in two-device browser testing must be completed on your deployment using the steps above. Keep the Nutrition migration and server records when rolling back only the frontend; do not downgrade the production database as a routine rollback.
