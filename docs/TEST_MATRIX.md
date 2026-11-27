# Release verification — 26 November 2026

Executed locally: 39 unittest cases passed + one separate browser integration workflow. Actual logs in `tests/`.

| Area | Tests | Expected behavior |
|---|---:|---|
| Analytics | 11 | Exact historical and plan totals; target effective dates; zero CAC denominator; duplicates/repeat scans; credit and walk-in; capacity/budget; transfer; experiment; invalid rates |
| Copilot/API | 15 | Fresh evidence; dates and engagement; tool loop including provider signatures and IDs; unknown evidence rejection; token redaction; task update; decline/confirm/expiry/stale revision; guarded transfer |
| Hosted release | 13 | Health; auth on pages/API; strict origin; locked secrets; JSON/NaN rejection; static allowlist/security headers; rate limit and concurrency; stale saves; six mutation cases; malformed patch; conflicting ID quarantine; fail-closed settings |
| Chromium integration | 1 workflow | Mock provider, real local API bridge; evidence UI, confirm/decline, dark theme, 390px layout, no page errors |

## Manual tests still needed on actual hosting
- Actual rotated Gemini credential, model access, tool-call response quality, rate/quota errors.
- Docker build and startup with mounted disk; Render deployment and health probe; HTTPS and Basic authentication through actual reverse proxy; cross-origin request rejection from actual browser.
- Save a task, restart service, verify persistence and that old confirmation token is rejected; restore backup.
- Check Chrome/Edge and mobile. Verify reviewer credentials work; check exact deck page count; confirm final URL is reachable from another network.
- Try unfamiliar prompts including unsupported numbers with valid citation IDs. Citation validation is not semantic proof; compare against evidence. Do not claim full production security or zero hallucinations.

## Vercel migration addendum (v4)
| Suite | Executed result |
|---|---|
| Original analytics | 11 passed (`tests/vercel-engine-results.txt`) |
| Original Copilot | 15 passed (`tests/vercel-copilot-results.txt`) |
| Original release/security | 13 passed (`tests/vercel-release-results.txt`) |
| Cloud adapter / RPC transport contract | 13 passed, mocked Supabase and Gemini (`tests/vercel-cloud-results.txt`) |
| Browser | Pass, 390px overflow, dark mode, evidence and confirmed/declined actions through serverless-handler bridge; mocked Supabase/Gemini (`tests/vercel-ui-results.txt`) |
| Real PostgreSQL schema / privileges / transactions | CI harness included (`tests/postgres_roles.sql`, `tests/postgres_contract.sql`); not executed in build environment |
| Vercel deployed runtime / Supabase project / real Gemini | Pending account-side validation |

Original workbook SHA-256 matches supplied file: `d63f3e013e9a823e28ab0a0587703b2ed4344e443ade185606c2ce3427203469`. The original `engine.py`, source JSON, HTML and CSS are unchanged from the final release. Tests use fake Supabase contract semantics; they do not prove the SQL runs on an actual database. CI creates a disposable PostgreSQL 16 instance, executes setup twice and checks RPC permission, state, revision, proposal and limit behavior. The SQL fixture test rolls back its writes; never execute fixture scripts in your real Supabase project. Run only `supabase/setup.sql` there.
