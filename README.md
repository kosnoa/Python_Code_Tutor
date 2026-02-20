# AI-Assisted Python Code Feedback (V1)

This is a local-first web product for beginner-to-intermediate Python learners.
It provides:

- static Python analysis (syntax checks + basic runtime-risk checks),
- structured, beginner-friendly explanations,
- 2-3 hint levels,
- optional solved version (via Gemini),
- optional time/space complexity hints.

V1 is anonymous and no code history is stored.

## 1) Backend setup (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and replace:

```
GEMINI_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE
```

Start backend:

```bash
uvicorn main:app --reload --port 8000
```

## 2) Frontend setup (Next.js + React)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The app runs at `http://localhost:3000`.

## 3) API contract (current)

`POST /api/analyze`

Request JSON:

```json
{
  "code": "print('hello')",
  "help_mode": "guided",
  "hint_depth": 1,
  "include_complexity": false,
  "include_solution": true
}
```

Legacy clients may still send `hint_level` instead of `hint_depth`.

Response JSON shape:

```json
{
  "summary": "...",
  "error_clusters": [],
  "hints": [{"level":"beginner","text":"..."}],
  "full_solution": {"code":"...","explanation":"..."},
  "key_concepts": [],
  "complexity": {"time":"...", "space":"..."},
  "best_practices": []
}
```

`help_mode` options:

- `guided` (default): hints and optional fixed code path.
- `diagnostic`: quick issue report with no hints/solution and minimal teaching extras.

## 4) Why this is safe for V1

- Static-only checks by default (no execution in this version).
- No user accounts and no persistence.
- API key is loaded from environment only.

When you are ready for launch, this can be moved to any free hosting:

- Backend: Render, Fly, or Railway.
- Frontend: Vercel.

## 5) Open source + GitHub publish

Goal: publish without committing secrets.

1. Verify secrets are ignored

```bash
cat .gitignore
git status --short
```

You should not see:
- `backend/.env`
- `backend/.env.local`
- `frontend/.env`
- `frontend/.env.local`
- `.env`
- `.env.local`
- `.venv`

If you see any, remove them from staging/history before publishing.

2. Create GitHub repo and push

```bash
git init
git branch -M main
git add README.md LICENSE backend frontend .gitignore render.yaml backend/.env.example frontend/.env.example
git commit -m "AI-assisted Python feedback app V1"
git remote add origin git@github.com:<your-github-username>/<your-repo-name>.git
git push -u origin main
```

If you already have a repo:

```bash
git remote add origin git@github.com:<your-github-username>/<your-repo-name>.git
git add README.md LICENSE backend frontend .gitignore render.yaml backend/.env.example frontend/.env.example
git commit -m "AI-assisted Python feedback app V1"
git push
```

## 6) Free web deployment (recommended)

Use this flow:
- Backend on Render (API)
- Frontend on Vercel (UI)

### 6.1 Deploy backend on Render

1. Go to Render and create a **new Web Service** from your GitHub repo.
2. Render will detect `render.yaml` automatically.
3. In service settings, set these values:
   - `GEMINI_API_KEY`: your Google AI Studio key
   - `ALLOWED_ORIGINS`: your frontend URL from Vercel (for example `https://your-app.vercel.app`)
4. Deploy.

After deploy, note your API URL:
`https://<render-service-name>.onrender.com`

Test endpoint:

```bash
curl https://<render-service-name>.onrender.com/healthz
```

### 6.2 Deploy frontend on Vercel

1. In Vercel, click **Add New Project** and import the repo.
2. Set **Root Directory** to `frontend`.
3. Add environment variable:

```text
NEXT_PUBLIC_API_URL=https://<render-service-name>.onrender.com/api/analyze
```

4. Deploy.

If deploy works, share the Vercel URL publicly and your GitHub repo will act as the open-source source of truth.

### 6.3 Share

- Share frontend URL from Vercel.
- Keep repo public to allow users to see source (without secrets).
- Keep `.env` files private and never commit them.
