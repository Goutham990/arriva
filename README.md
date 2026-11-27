# ARRIVA Studio — From Intent to Attendance
RISA Growth APM · Challenge A · Final submission — Vercel + Supabase edition (v4) | Goutham Karamtoth

## Deploy on Vercel (free-tier route)
Use [the full step-by-step deployment guide](docs/DEPLOYMENT.md) and [Supabase SQL setup](supabase/setup.sql). The same existing frontend and Python analytics/AI routes run in a single Vercel function (`api/entry.py`); the hosted state store uses Supabase PostgreSQL through a restricted HTTPS RPC. Local Windows mode still works without Supabase. No live cloud deployment has been performed.

## Start in 60 seconds
1. Extract the ZIP. Install Python 3.10+ if not already installed. No pip or npm dependencies.
2. On Windows double-click `START_WINDOWS.bat`, or in a terminal run `py server.py` / `python server.py`. On macOS/Linux use `python3 server.py`.
3. Open `http://127.0.0.1:8080` in Chrome, Edge or Firefox. Keep the terminal open. Do not open `web/index.html` directly; the application needs its local API.
4. Click the sun/moon in the header, or Settings → Appearance, to select light/dark/system theme. Selection is stored in localStorage. The rest of the workspace is saved to SQLite in `data/workspace.sqlite3`.

## Gemini Copilot setup
The app uses Google's Gemini generateContent REST API with `x-goog-api-key`. The supplied chat credential is deliberately not embedded in the downloadable files. Rotate any key shared in a conversation or source code before deploying. Generate a replacement at https://aistudio.google.com/apikey, then open ARRIVA → Settings → Gemini AI connection. Paste the key, select a model ID (default `gemini-3.8-flash`, configurable), click Connect / update and Test connection. Check the model available to your Google account if the provider returns 404. Credential stays only in the local Python process's memory, never in localStorage, SQLite, exported backups, or frontend source. It is cleared on server restart. Alternatively start with `python server.py --prompt-key` to enter a hidden credential at the terminal, or use `GEMINI_API_KEY` and `GEMINI_MODEL` environment variables. Local mode binds to loopback. Hosted reviewer mode requires HTTPS origin and reviewer credentials; API configuration is server-managed. See docs/DEPLOYMENT.md. API usage may be billed by Google. The Gemini integration requires internet access; all deterministic analytics and management remain usable without an API key.

## Features and controls
- Two independent workspaces: original synthetic CampusFest 2025 historical data and hypothetical Spring Fest Kolkata metropolitan edition.
- Dark, light and system appearance; responsive navigation; KPI cards; funnel, line and comparison charts.
- Historical snapshots, target versioning, deduplication, registered cohort show-up, anonymous activity and net spend.
- Editable campaigns, base/stretch assumptions, owners, status, observed funnel, thresholds, budgets and confidence weights; task CRUD, experiment CRUD, scenario constraints, audit logs, data mutation controls, JSON export/import and reset.
- Scenario simulator previews transfer, calculates new reach and capacity-constrained forecast, then saves only with explicit confirmation. Constant source average CAC and chosen destination marginal CAC are assumptions; saturation is not modelled.
- AI Copilot free-form multi-turn conversation, fresh aggregate context each turn, real Gemini function calling, source labels, deterministic calculations, explicit missing-data limitations and server-side confirmation tokens for tasks/budget proposals. Confirmation tokens expire after 15 minutes and are tied to workspace revision. The model cannot write directly. Conversation is session-local, not persisted. Without Gemini use the deterministic analysis buttons; these are labelled as such.
- Local SQLite or hosted Supabase PostgreSQL with optimistic revision checks. Backups omit credentials and preserve original immutable dataset. Historical mutation patches are reversible; do not treat them as actual external event observations.

## Data and strategy reconciliation
Original workbook is included unaltered, with all 11 worksheets extracted into `data/source.json` by `ingest.py`. Source sheets contain synthetic CampusFest records. Original end-of-day 20 Apr 2025: 3,625 identified external people, 3,500 campaign-acquired, 2,800 registrations, 1,925 verified registered visitors + 125 walk-ins = 2,050 distinct verified external visitors, ₹274,000 net marketing spend, ₹133.66 blended attendance CAC. 2,775 visitor-days, 3,250 verified external admissions. Dedup removes 2 activity retries, 4 status-history retries and 20 gate retries; conflicting IDs are quarantined. Snapshots filter events by local date; latest effective registration status and goal; distinct external person IDs, not gate scans. First recorded acquisition campaign is attribution, not causality. Anonymous reported reach is not globally distinct people. Zero denominator returns N/A. Walk-ins are unattributed. Vendor credits reduce net spend.

Spring Fest simulated plan follows the final ARRIVA deck: 50,280 base / 67,300 stretch visitors; 67,400 / 90,000 registrations; ₹60L / ₹82L planned marketing budget; ₹119.33 / ₹121.84 forecast CAC. Five bets: College Growth Network, Squad Pass, City Culture Takeover, Artist-to-Audience Flywheel, Precision Paid. Stretch 47,000 BAU and +20,300 hypothesized lift, not measured causal effect. Capacity uses 2,775/2,050 historical repeat factor, 3 days, 10% reserve and illustrative daily visitor-day capacity 26k/34k. Actual peak occupancy, gate safety and venue approval are unknown. Forecasts use exclusive assigned audiences; no additional walk-in contribution. Experiment lift = treatment size × (treatment rate − control rate); incremental CAC uses treatment cost less scaled control cost divided by positive lift. Screening floors are ≥7 days plus 200 eligible people per arm or 30 college clusters; not formal power estimates. Budget/capacity and uncertainty checks override scale recommendations.

## Phase 5 — AI Growth Analyst and Copilot
The previous ARRIVA Studio source was retained and extended; the existing dashboard, campaign and task management, scenario controls, experiments, mutation sandbox, themes and backup/restore remain. An existing Studio SQLite workspace can be reused with `python server.py --db /path/to/workspace.sqlite3` (make a backup first). The new Copilot keeps a bounded multi-turn history in the browser tab and sends it as explicitly untrusted context alongside fresh evidence for each request. There is no durable chat archive; workspace actions are durable.

### Tool catalogue
| Tool | Purpose |
|---|---|
| `historical_metrics` | As-of historical funnel, status, targets, net spend and CAC |
| `compare_campaigns` | Comparative first-campaign attribution across historical channels |
| `historical_trend` | Date-range cumulative snapshots; no future leakage |
| `engagement_metrics` | Deduplicated external interactions and distinct people by event type |
| `diagnose_campaign` | Historical conversion gap or simulated observed performance, thresholds and experiments |
| `planning_metrics` | Current base/stretch model, alerts, capacity and budgets |
| `simulate_constraints` | Read-only what-if capacity, budget, target, campaign reach/rates/budget |
| `simulate_transfer` | Read-only reallocation forecast; user chooses marginal CAC |
| `execution_metrics` | Current saved tasks and experiment results |
| `data_quality` | Source row reconciliation and explicit missing-data boundaries |
| `propose_task` | Draft new task; no workspace write |
| `propose_task_update` | Draft status/owner/priority/deadline/name changes to existing task |
| `propose_transfer` | Draft plan-only budget reallocation; checks budget and capacity |

Gemini uses `generateContent` with declared function schemas. The complete returned content (including thought signatures and function-call IDs when supplied) is preserved during tool loops. Requests are bounded to 7 model rounds and 12 tool calls. Every turn starts with a current snapshot and data limitations. Results receive server-issued evidence identifiers, scope, tool parameters and revision; the UI displays expandable exact aggregate results. The response is withheld if it has no valid citation or cites an unknown ID. Citation validity is not proof that every statement or calculation in the narrative is correct. The deterministic tool outputs remain the authoritative figures. No raw attendee names are sent to Gemini by these tools; workspace task names and user messages are sent to the provider. Do not include sensitive information in chat or tasks.

Proposal tokens are random, held in local memory for SQLite mode or hashed in Supabase PostgreSQL for Vercel mode, excluded from LLM context, single-use, expire after 15 minutes and bind to the exact revision. User confirmation is a separate endpoint, not a tool exposed to the model. Decline revokes the token; stale or expired proposals cannot execute. The server rechecks constraints before saving a transfer. Saving updates the workspace database, app analytics and audit history. A forecast is not a transaction or actual external communication.

### Evaluator demo script (after connecting Gemini)
1. In Historical Lab on 20 April 2025, ask: “Compare Paid Social and College Partnerships; diagnose the biggest funnel bottleneck.” Verify against the tool evidence: 340 vs 385 arrivals, 50% vs 85.56% show-up, CAC ₹273.53 vs ₹80.52. These are associations, not proof of causation.
2. Follow up: “Show the cumulative verified gate arrivals on April 11, 12 and 13.” Expected 0, 1,430, 2,050. Ask “Which individual colleges were best?” The dataset has no college IDs; the response should acknowledge the gap.
3. Use Data & audit → add the ₹5,000 credit. Return to Copilot, ask “What is net spend now?” Expected ₹269,000 at the final snapshot; old answers are marked as older revisions. Reset the sandbox afterward.
4. Switch to Spring Fest. Ask “What if stretch daily capacity is 20,000 visitor-days?” Expected feasible ceiling 39,891, with no change to the saved 67,300 plan. Ask “Simulate shifting ₹20,000 from Precision Paid to Squad Pass at ₹100 destination marginal CAC.” Compare preview and then ask to prepare the transfer. Approve only after inspecting the values; budget remains unchanged overall.
5. Ask “Draft a task for the Growth Lead to audit paid show-up.” Review evidence and exact change, then confirm. Open Execution Board and inspect the saved task. Follow up with a status update, or decline a second draft. Reload the app to verify task persistence.
6. Create a draft then manually change campaign data before confirming; the revision guard blocks stale approval. This is intentionally stricter than blindly accepting the model's recommendation.

### Tests and limitations
52 automated tests passed (11 analytics, 15 Copilot/API, 13 original hosted-mode release tests, 13 Vercel adapter and mocked Supabase RPC/transport tests), plus a separately executed serverless-handler Chromium integration test. See `tests/*-results.txt` and `docs/TEST_MATRIX.md`. Browser test used an isolated fetch bridge to actual local handlers and a mocked provider; it did not exercise a real HTTPS host. No live Gemini credential/model/quota test, deployed URL, Docker image build or cloud restart test has been performed in this environment. The supplied key is excluded; use a rotated key and a model available to your account. Citation identifiers are validated but do not prove all narrative claims. Check exact tool evidence. Hosted mode is a single shared, password-protected reviewer workspace, not a multi-tenant service. Vercel mode persists workspace, approval tokens, request limits and concurrency leases in PostgreSQL. Local or legacy Render SQLite mode requires one process and a durable disk. The SQL integration harness is included in GitHub Actions, but a real PostgreSQL instance was not available in the build environment; execute SQL setup and live tests before submission. No real marketing expenditure, actual gate integration, attendance guarantees or independent security audit. Provider charges may apply.

## Architecture
`server.py` shared local/hosted HTTP + SQLite/Supabase persistence + Gemini tools; `api/entry.py` Vercel request adapter; `cloud_store.py` Supabase REST transport; `supabase/setup.sql` transactional database functions; `engine.py` shared analytics; `web/` frontend; `data/` immutable workbook/extracted JSON; `ingest.py` extraction; `tests/` tests and UI previews. API key handling is server-side only. Official Gemini documentation: https://ai.google.dev/gemini-api/docs and https://ai.google.dev/gemini-api/docs/function-calling.

## Research, assumptions and prioritization
The original RISA assignment, pages 1–4, requires exactly three slides, a working product/demo, and a README. Challenge A targets actual attendance, not registrations. The source workbook is fictional; workbook SHA-256 `d63f3e013e9a823e28ab0a0587703b2ed4344e443ade185606c2ce3427203469` matches the supplied original. The festival scenario is inspired by IIT Kharagpur Spring Fest but is explicitly a hypothetical Kolkata metropolitan edition to satisfy the Tier-1-city requirement. Metro accessibility and college/cultural communities motivate the location. Public scale context (not unique-person attendance evidence): [The Avenue Mail, 26 Dec 2024, Spring Fest preview](https://avenuemail.in/iit-kharagpurs-spring-fest-from-january-24/). No confirmed venue, individual college list, measured overlap, actual event operating budget or platform-unique reach is supplied.

| Bet | Base reach / reg % | Stretch reach / reg % | Show-up | Visitors base / stretch | Budget base / stretch | BAU stretch lift | AICE |
|---|---:|---:|---:|---:|---:|---:|---:|
| College Network | 60k / 35% | 80k / 35% | 80% | 16,800 / 22,400 | ₹19L / ₹26L | 7,400 | 600 |
| Squad Pass | 70k / 20% | 90k / 20% | 75% | 10,500 / 13,500 | ₹10L / ₹13L | 4,050 | 750 |
| City Culture | 180k / 8% | 200k / 10% | 70% | 10,080 / 14,000 | ₹9L / ₹14L | 3,600 | 510 |
| Artist Flywheel | 20k / 50% | 28k / 50% | 85% | 8,500 / 11,900 | ₹10L / ₹14L | 3,500 | 468 |
| Precision Paid | 160k / 5% | 250k / 4% | 55% | 4,400 / 5,500 | ₹12L / ₹15L | 1,750 | 220 |
| Total | 490k | 648k | weighted | 50,280 / 67,300 | ₹60L / ₹82L | 20,300 | — |

Reach counts are exclusive hypothetical assigned cohorts, not anonymous reach totals. Stretch sizing: 800 activated college nodes ×100 eligible students, 18k advocates ×5 invites, 400 city groups ×500, 1,400 artist nodes ×20 contacts, 250k additional paid audience after exclusions. Activated colleges are not guaranteed represented colleges. Round reach × registration rate, then registrations × show-up; sum visitors, cap at floor(daily visitor-day capacity ×3×0.90 / (2775/2050)). Budget divided by feasible visitors gives marketing CAC. Baseline to stretch expansion 17,020 for ₹22L (~₹129.26/extra forecast visitor). BAU uses reg/show respectively College .25/.75, Squad .15/.70, City .08/.65, Artist .40/.75, Paid .03/.50; sum 47,000, difference 20,300 is already in stretch. AICE = base-to-stretch expansion × judgmental confidence (.75/.75/.65/.55/.60) / additional budget in lakh. College first for seeding dependencies even though Squad scores higher. Historical college/referral spend share 18.2% vs 34.3% attributed attendance; paid/creator spend 55.5% vs 26.8%. Stage releases ₹6L pilot, ₹18L validation, ₹36L base, ₹22L conditional stretch. Broad creator spending, celebrity-first buying and raw-registration rewards deprioritized. Costs exclude production/venue/security. Thresholds: college ≥35% scale/<20% stop; squad CAC ≤₹110/>₹150; city ≥10%/<5%; artist ≥50%/<30%; paid CAC ≤₹275/>₹350. Middle ranges change; sufficient pilot samples and capacity/budget constraints required. Proposed pacing at T−10/8/6/4/2 weeks/event is 5/15/35/60/85/100% registrations; investigate below 80% of pace.

## Submission and hosting
- `docs/ARRIVA_Strategy.pdf`: exact three-slide deck. Editable PowerPoint is included in the full submission bundle.
- `docs/DEPLOYMENT.md`: Vercel + Supabase, environment secrets, GitHub, preflight and rollback.
- `docs/DEMO_SCRIPT.md`: concise evaluator walkthrough with numerical expectations.
- `docs/TEST_MATRIX.md`: actual test coverage and manual checks.
- `vercel.json`, `supabase/setup.sql`, `.github/workflows/ci.yml`: Vercel deployment and CI configuration. Legacy Render/Docker files are retained for compatibility but are not needed for Vercel. Vercel Hobby and Supabase Free are subject to eligibility and limits. Public hosting has not been provisioned. Provide the eventual HTTPS URL and reviewer password privately; do not commit secrets.

Tools used: ChatGPT for iterative strategy/code drafting, Python standard library and SQLite for deterministic analytics/persistence, native HTML/CSS/JS and SVG for UI, Google Gemini REST API for free-form reasoning/function calling, unittest and optional Playwright for testing; PowerPoint/PDF for slides. Original source records retained; forecasts, decisions and confidence weights are proposed assumptions. The candidate should review the calculations, run the demo personally and be able to explain the design and AI usage transparently.
