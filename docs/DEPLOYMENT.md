# ARRIVA Studio v4 — Vercel + Supabase + Gemini

This guide deploys both frontend and backend as a **single Vercel project**, backed by Supabase PostgreSQL. No Render service, paid disk, separate frontend project or npm build is needed. The application is prepared for deployment; actual Vercel builds, Supabase SQL execution and live Gemini calls must be verified in your accounts.

## 0. Local check (same Windows workflow)
Extract the ZIP to a new folder, e.g. `C:\ARRIVA_Vercel`, preserving hidden files. In PowerShell from the folder containing `server.py`, run `python --version`, then `python server.py` (or double-click `START_WINDOWS.bat`). Open `http://127.0.0.1:8080`. Local mode still uses SQLite and your existing Windows `GEMINI_API_KEY` / `GEMINI_MODEL` environment variables. It does not need Supabase. Do not set `ARRIVA_STORAGE=supabase` for the normal local demo. `.env.example` is a reference, not an automatically loaded file. If desired export the local workspace from Settings before migration; do not copy SQLite into GitHub.

## 1. Create the free Supabase project
1. Sign in at https://supabase.com/dashboard and create a new project (Free plan, if eligible). Select a nearby region, e.g. Singapore if available. Set a strong database password, saved privately; the application does not need the password.
2. Wait for project provisioning to complete. Choose **SQL Editor → New query**.
3. Open `supabase/setup.sql` in VS Code, copy the complete SQL, paste it into the editor, and select **Run**. This is idempotent and does not reset existing data. It creates the private `arriva_private` schema (workspace, proposals, request events and AI leases) and the restricted public RPC `arriva_rpc`. Keep the Data API enabled with `public` exposed; do not expose `arriva_private`.
4. Find the project URL in the **Connect** dialog or Project Settings → Data API: `https://<project-ref>.supabase.co` (no `/rest/v1` suffix).
5. In Project Settings → API Keys, copy a **server-side secret key** (starts `sb_secret_`) under secret keys. If only legacy keys are available, copy the **service_role** key and use the alternative variable below. Do not use the publishable/anon key. Do not put either secret into client code, chat, GitHub, or screenshots. A new secret key is sent only as `apikey`; legacy JWT service-role keys use both `apikey` and Bearer authorization. The app calls the Supabase HTTPS Data API; no database connection string, pooler configuration or dependency installation is needed.

### Check the SQL setup
The SQL Editor should report success. In a new SQL query you can run this read-only check (owner session):
```sql
select public.arriva_rpc('load', '{}'::jsonb);
```
On a fresh deployment this returns `{"ok":true,"state":null}`. The app automatically shows the seeded Phase 2 baseline until the first save creates the workspace row. No extra seed SQL or spreadsheet import is required. Original synthetic workbook is bundled unchanged; `data/source.json` remains the immutable baseline. Only editable workspace state, revisions, mutations, audit, proposal hashes and limits are stored in PostgreSQL.

## 2. Upload the new version to GitHub
Use a NEW private repository (e.g. `arriva-vercel`) so your working Render/local repository remains untouched. Go to https://github.com/new, create a repository without a generated README, and then from the extracted project root in PowerShell:
```powershell
git init
git add .
git status
git commit -m "ARRIVA Studio Vercel Supabase release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/arriva-vercel.git
git push -u origin main
```
Check staged files: no `.env`, real API keys, `.sqlite3`, backups with private data or `.vercel/` directory. Do not embed keys in START_WINDOWS.bat. Replace username. Use GitHub login if prompted. Repository root must contain `vercel.json`, `api/entry.py`, `server.py`, `engine.py`, `web/`, `data/source.json`, `supabase/`. Keep the original workbook in the private source repo for evaluator access; deployed static files exclude it. If you instead update an existing repo, use an ordinary commit and push, not force push.

## 3. Create the Vercel project
1. Sign in at https://vercel.com/new with GitHub. Import the new private repo. Authorize Vercel for that repo only if needed.
2. Pick **Other** framework preset, root directory `./` (the folder containing `vercel.json`), project name `arriva-vercel` or your own available name. Do not select `web/` or `api/` as root. Leave build/install settings as supplied by `vercel.json`; no npm build command. Output directory `public` contains only robots.txt; protected HTML/CSS/JS are served through the Python function. Enable Fluid compute if the setting appears (300-second maxDuration is configured and needs a compatible plan/settings). Do not add a custom start command.
3. Add these variables in Environment Variables before deploying (or add them under Project → Settings → Environment Variables and redeploy). Select Production. Do not use NEXT_PUBLIC_ or other frontend prefixes. You may set `ARRIVA_ORIGIN` to the actual assigned production domain after the first deployment and then redeploy. If absent, the backend uses Vercel's `VERCEL_PROJECT_PRODUCTION_URL` system variable when available; explicit origin is the reliable choice.

| Name | Value |
|---|---|
| `ARRIVA_STORAGE` | `supabase` |
| `SUPABASE_URL` | `https://YOUR_PROJECT_REF.supabase.co` |
| `SUPABASE_SECRET_KEY` | Supabase server-side secret key (`sb_secret_...`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Alternative legacy key only; omit if using `SUPABASE_SECRET_KEY` |
| `GEMINI_API_KEY` | Your rotated, locally tested Google Gemini key |
| `GEMINI_MODEL` | Exact model ID shown in your working local Settings (no `models/` prefix) |
| `ARRIVA_REVIEW_USER` | `reviewer` |
| `ARRIVA_REVIEW_PASSWORD` | Unique strong password, at least 16 characters |
| `ARRIVA_ORIGIN` | Actual `https://YOUR-PROJECT.vercel.app`, no trailing slash/path |

Hosted auth and Supabase mode are forced by the Vercel handler regardless of `ARRIVA_PUBLIC`. Do not set `ARRIVA_DB` or `PORT`; Vercel handles the listener. If you set different preview credentials, use a separate Supabase project for previews to avoid touching production. Use the stable production domain; branch/preview URLs are not approved POST origins. After changing env vars, redeploy.

4. Click **Deploy**. On success, copy the actual production domain from the project dashboard. If it differs from your configured `ARRIVA_ORIGIN`, correct the value and redeploy (Settings → Environment Variables; Deployments → Redeploy). If using Vercel deployment protection, ensure the final production domain can be reached by a non-Vercel reviewer; keep ARRIVA's own Basic auth enabled. Do not share a deployment URL requiring your personal Vercel account.

## 4. Verify the hosted application
Open the stable `https://<your-project>.vercel.app/health` URL. Expected: `{"status":"ok"}`. Visit the homepage in an incognito window. Enter the reviewer username/password in the browser prompt. In Settings, the hosted API key is already configured and cannot be changed in the UI; select Test connection. If it fails, check the model and key in Vercel, redeploy, and retry. Gemini quotas/availability are account-dependent. The app never silently pretends a mock response is real.

Expected results: Historical Lab 20 April 2025: 2,050 visitors, 2,800 registrations, ₹274,000 spend, ₹133.66 CAC. Spring Fest: 50,280/67,300 base/stretch, ₹60L/₹82L. Check both themes. Create a task and reload in a new window; check that task persists. Make a new Git deployment or redeploy, and verify again. Ask Copilot to compare Paid Social and College Partnerships; then ask a follow-up and request a draft task. Confirm or decline in the UI. The token must work across independent invocations; stale actions should fail. Use Data quality to add a ₹5,000 credit, verify ₹269,000 spend, then reset the sandbox. Confirm historic sources and simulated plan are separated. Do not submit until these live tests pass.

If you want the exact workspace from your old local app, export a JSON backup using Settings → Export, then import on the hosted app via Settings → Import backup. No local DB copy needed; the import is validated and uses the hosted revision/audit system. Keep a private export for recovery. For the evaluator, restore the seeded demo if desired; reset affects the shared workspace, so confirm before doing so. Share your real HTTPS link, reviewer username/password privately and the final three-slide PDF + README. Revoke/rotate credentials or disable the deployment when review is over.

## Troubleshooting
| Symptom | Check |
|---|---|
| 503 hosted configuration incomplete | Vercel env vars, exact HTTPS origin, reviewer password >=16 chars, Supabase project URL and secret; redeploy after edits |
| `/health` 503 | Supabase project is running (free projects can pause), SQL setup executed, key and URL correct, Data API enabled, schema cache refreshed |
| 401 | ARRIVA reviewer credentials; try a new incognito window; production domain must be accessible without Vercel account login |
| 403 on POST | `ARRIVA_ORIGIN` equals browser address origin; open production domain, not preview; config endpoint is intentionally locked |
| 404 on root or `/api/dashboard` | Root directory must contain `vercel.json` + `api/entry.py`; Other preset; output directory public; check Vercel function build log |
| Gemini 400/403/404 | Use same working local key/model; check quota and API permissions; do not assume default model exists |
| Gemini 429 | Account quota or application rate limit; wait, narrow question, check Google usage |
| AI busy | Two concurrent model calls allowed; expired cloud leases recover automatically after 330 seconds |
| 409 after confirmation/save | Another reviewer changed the revision; reload and regenerate proposal |
| Missing source file on cloud | Commit `data/source.json`, confirm includeFiles and root; don't deploy only web/ |
| Function timeout | Fluid compute enabled, `maxDuration=300` supported; ask smaller questions; Gemini loop has bounded time and tool calls |
| No data persists | Do not use local mode on Vercel; verify `/api/config` reports Supabase PostgreSQL; inspect SQL setup/connection; don't reset before testing |

## Security, cost and operational limits
- Vercel Hobby is for eligible personal/non-commercial use only; confirm your placement demo qualifies. Supabase Free currently allows 500 MB DB storage and may pause after roughly one week of low activity. Gemini free-tier availability and quota depend on account/model. This architecture can run with no hosting charges within qualifying free allowances, not a guarantee of zero cost. Review limits and do not enable unnecessary paid options. Restore paused Supabase before reviewer access; do not add artificial keep-alives. Official references: https://vercel.com/docs/plans/hobby, https://vercel.com/docs/functions/runtimes/python, https://vercel.com/docs/functions/configuring-functions/duration, https://supabase.com/pricing, https://supabase.com/docs/guides/getting-started/api-keys, https://ai.google.dev/gemini-api/docs/rate-limits.
- Single shared authenticated reviewer workspace, not multi-tenant. Basic auth behind HTTPS protects page assets and API except minimal `/health`. Exact Origin on JSON POST, no key exposure, CSP/HSTS, rate limits shared via DB (12 AI/min, two concurrent; 60 writes and 180 reads per minute), atomic compare-and-swap revision writes and 15-minute single-use proposal tokens stored as SHA-256 hashes. Confirmation and token consumption occur in one PostgreSQL transaction. RLS and explicit GRANT/REVOKE protect private tables/RPC from anon/authenticated roles. Server-only secret key has broad project access: protect it, use a dedicated demo Supabase project, never use it in browser. Browser chat history remains session-local and explicitly untrusted; confirmed workspace actions are durable. No external security audit, per-user data isolation, production SLA or guarantee of numerical correctness of every model narrative.
- Validation here: 39 original regression tests plus 13 mocked cloud transport/router/RPC tests passed (52 total); isolated Chromium browser workflow passed with mock providers; original dataset identical. PostgreSQL itself and the real Vercel runtime/Gemini were not reachable in this environment. GitHub Actions includes a disposable real PostgreSQL service to run SQL setup twice and check permissions, revisions, proposals and rate limits. Wait for CI to pass and run live health/auth/AI/redeploy checks before submission.
