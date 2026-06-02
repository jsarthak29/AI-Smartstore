# Deploy SmartStore AI

End-to-end guide to ship SmartStore AI to the public internet on free tiers:

| Piece | Host | Plan |
|---|---|---|
| Postgres | Supabase | Free |
| FastAPI backend (Docker) | Render | Free web service |
| React/Vite frontend | Vercel | Hobby |

Total time: ~25 minutes if you have the accounts already. Pick one path in §3 (Blueprint or manual) — don't do both.

---

## 0. Prerequisites

Accounts (all free):

- [GitHub](https://github.com)
- [Supabase](https://supabase.com)
- [Render](https://render.com) — sign in with GitHub
- [Vercel](https://vercel.com) — sign in with GitHub

Push the repo to GitHub first. Either via the GitHub CLI:

```powershell
gh repo create smartstore-ai --public --source=. --remote=origin --push
```

…or via the web UI: create an empty repo at https://github.com/new, then from the repo root:

```powershell
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/<your-user>/smartstore-ai.git
git push -u origin main
```

Sanity check before you continue: `.env` is **not** committed (it's gitignored), and `.env.example` **is**.

---

## 1. Supabase — provision Postgres

1. https://supabase.com/dashboard → **New project**.
2. Name: `smartstore`. Region: closest to you. Set a strong DB password — Supabase will show it once, save it.
3. Wait ~2 minutes for the project to finish provisioning.
4. Go to **Project Settings → Database → Connection string → URI**. Copy the value. It looks like:

   ```
   postgresql://postgres:[REDACTED-PASSWORD]@db.[REDACTED-PROJECT-REF].supabase.co:5432/postgres
   ```

   Use the direct connection (port `5432`), not the connection pooler — Alembic and asyncpg both want a real Postgres endpoint.

> The URI contains your DB password in cleartext. Treat it like a secret. Don't paste it into chat, screenshots, or commits.

You only need this **one** URI. The app's config auto-derives the asyncpg (runtime) and psycopg2 (Alembic) variants from it, and appends `ssl=require` / `sslmode=require` automatically. You'll paste it into Render as `DATABASE_URL` in §3.

---

## 2. (Optional) Pre-seed Supabase from local

The backend Dockerfile runs `alembic upgrade head && python -m app.seed` on boot, so migrations and seeding happen automatically when Render starts the service. **You can skip this section** unless you want to verify the schema lands in Supabase before deploying.

If you do want to pre-seed, open PowerShell at the repo root:

```powershell
cd backend
.venv\Scripts\activate                     # (or `python -m venv .venv` first if missing)
pip install -r requirements.txt
```

Set the plain Supabase URL — config.py rewrites the driver scheme:

```powershell
$env:DATABASE_URL="postgresql://postgres:YOUR-PASSWORD@db.YOUR-REF.supabase.co:5432/postgres"
```

> URL-encode the password if it contains `@`, `#`, `:`, `/` or `?` (e.g. `@` → `%40`).

Run migrations and seed:

```powershell
alembic upgrade head
python -m app.seed
```

Expected output: `[seed] tenant 'Raj Grocery' created`, `[seed] tenant 'Demo Mart' created`. The seed is idempotent — re-running prints `already exists, skipping`.

Verify in the Supabase dashboard → **Table editor** → `tenants`, `users`, `products`, `suppliers` etc. should all be populated.

---

## 3. Render — deploy backend

Two paths. **Path A** is the one-click Blueprint flow that picks up `render.yaml` from the repo. **Path B** is point-and-click in the dashboard. Pick one.

### Path A — Blueprint (recommended)

1. https://dashboard.render.com → **New +** → **Blueprint**.
2. Connect the GitHub repo. Render reads `render.yaml` from the repo root.
3. Render will list the env vars marked `sync: false` and ask you to fill them in **before** the first deploy:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | `postgresql://postgres:YOUR-PASSWORD@db.YOUR-REF.supabase.co:5432/postgres` — paste the Supabase URI as-is. The app auto-derives the asyncpg + psycopg2 variants and adds SSL. |
   | `JWT_SECRET` | A long random string. Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `GEMINI_API_KEY` | Your key from https://aistudio.google.com |
   | `FRONTEND_ORIGIN` | Leave as `http://localhost:5173` for now — update in §5 after Vercel gives you a URL. |
   | `SEED_ADMIN_PASSWORD` | `admin123` (or pick your own — used by the seed script on first boot) |
   | `SEED_STAFF_PASSWORD` | `staff123` (or pick your own) |

4. Click **Apply**. Render builds the Docker image and boots it. First build is ~5 minutes.
5. When the service is **Live**, note its URL (looks like `https://smartstore-backend.onrender.com`). Open `https://smartstore-backend.onrender.com/health` — you should see `{"status":"ok"}`.

### Path B — Manual web service

1. https://dashboard.render.com → **New +** → **Web Service**.
2. Connect the repo. Settings:
   - **Name:** `smartstore-backend`
   - **Region:** closest to your Supabase region
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Docker`
   - **Plan:** Free
   - **Health check path:** `/health`
3. **Environment** → add the same variables listed in Path A.
4. **Create Web Service**. Build + deploy.
5. When **Live**, hit `/health` to confirm.

The backend now talks to Supabase. CORS still rejects the (not-yet-created) Vercel origin — we fix that in §5.

---

## 4. Vercel — deploy frontend

1. https://vercel.com/new → import the GitHub repo.
2. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` *(default)*
   - **Output Directory:** `dist` *(default)*
3. **Environment Variables** → add both, scoped to **Production, Preview, Development**:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://smartstore-backend.onrender.com` |
   | `VITE_WS_URL` | `wss://smartstore-backend.onrender.com` |

   Replace `smartstore-backend` with your actual Render service name. **`wss://`** — not `ws://` — Vercel serves over HTTPS and the browser will refuse a plain WS connection.
4. **Deploy**. ~2 minutes.
5. Note the production URL (looks like `https://smartstore-ai.vercel.app`).

---

## 5. Wire CORS

The backend's `FRONTEND_ORIGIN` controls which origin can call the API. Update it now.

1. Render Dashboard → `smartstore-backend` → **Environment**.
2. Edit `FRONTEND_ORIGIN` → set to your Vercel URL, e.g. `https://smartstore-ai.vercel.app` (no trailing slash).
3. **Save changes** — Render auto-redeploys (~2 minutes).

---

## 6. Verify

Open the Vercel URL. Run the assessment smoke test (§11 of the README):

- [ ] Log in as `admin@smartstore.app` / `admin123`. Dashboard loads with stock-health cards.
- [ ] Log in as `staff@smartstore.app` / `staff123` in another browser. Try to send a PO email — you get a 403.
- [ ] Add a product with stock below threshold → row shows red on `/products`.
- [ ] Open a product detail → forecast chart renders.
- [ ] Open the AI chat → ask "Which products will run out in 7 days?" — response cites real SKUs with a tool chip.
- [ ] Ask the chat to "draft a PO for our lowest-stock supplier" → a Draft PO appears in `/purchase-orders`.
- [ ] Upload `docs/sample_invoices/invoice_01.png` → review parsed lines → confirm → stock increments, toast fires in another tab.
- [ ] On `/automation`, click **Run low_stock_agent** → POs appear + a log row is written.
- [ ] Log in as `admin2@smartstore.app` / `admin123` → confirm Demo Mart cannot see Raj Grocery's data.

---

## 7. Known gotchas

- **Render free spin-down.** The web service sleeps after ~15 minutes of inactivity. The next request takes ~30s to wake it. Acceptable for a demo; don't panic-debug a slow first request.
- **Supabase free pause.** Projects pause after 7 days of inactivity. Click **Restore** in the dashboard if your demo is older than that.
- **Seed errors on first deploy.** If your Render logs show seed-script errors mentioning `tenant 'Raj Grocery' already exists, skipping`, that's expected — the seed is idempotent. Any actual crash means migrations weren't run; redo §2.
- **Mock email.** `POST /purchase-orders/{id}/send-email` writes to stdout (visible in Render logs) — there's no real SMTP integration. Not a deploy bug.
- **WebSocket scheme.** Vercel forces HTTPS. `VITE_WS_URL` **must** be `wss://`, not `ws://`. The chat and the realtime stock toasts both fail silently otherwise.
- **Just one DB URL.** Set `DATABASE_URL` to the plain Supabase URI; `backend/app/config.py` auto-derives the asyncpg + psycopg2 variants and appends SSL. Don't set `SYNC_DATABASE_URL` manually on Render — it'll either be ignored or fight the auto-derive.
- **Ephemeral uploads.** Render free plan has no persistent disk. Uploaded invoices live in the container filesystem and disappear on redeploy / sleep. Switch the plan to `starter` and uncomment the `disk:` block in `render.yaml` to keep them.
- **Password special chars.** Supabase auto-generates DB passwords that may contain `@` or `#`. URL-encode them in the connection string or you'll see `could not parse` from asyncpg.

---

## 8. Rolling back / re-seeding

If you need to wipe Supabase and start fresh:

```powershell
cd backend
.venv\Scripts\activate
$env:DATABASE_URL="postgresql://postgres:YOUR-PASSWORD@db.YOUR-REF.supabase.co:5432/postgres"

alembic downgrade base
alembic upgrade head
python -m app.seed
```

Alternative (nuclear): Supabase Dashboard → **Project Settings → General → Reset database**. Then run §2 again.

To roll back the Render backend to a previous build: Render Dashboard → **Events** → pick a prior deploy → **Rollback**.

---

## Done — submission checklist (assessment §9.4)

- [ ] Repo is public on GitHub.
- [ ] `README.md` covers architecture, setup, the six modules, forecast rationale, LLM choice.
- [ ] `.env.example` present at repo root; real `.env` is gitignored.
- [ ] `docker-compose up --build` builds cleanly from a fresh clone.
- [ ] All 6 modules working: Inventory, Suppliers + POs, AI Chat, Forecast, Invoice OCR, Automation.
- [ ] AI assistant has ≥ 3 tools wired (this build ships 5).
- [ ] Two sample invoices in `docs/sample_invoices/`.
- [ ] Demo video link added to README §15.
- [ ] ≥ 15 commits in `git log` (target 30).
- [ ] Live URLs noted: backend `https://<your-render-app>.onrender.com`, frontend `https://<your-vercel-app>.vercel.app`.
