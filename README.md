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
