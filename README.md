# AI-Assisted Python Code Feedback (V1)

AI-Assisted Python Code Feedback is a web-based tutor for beginner-to-intermediate Python learners.
It analyzes pasted Python code and returns structured, beginner-friendly feedback designed for learning
instead of just providing a direct answer.

## What this project does

- Parses and analyzes submitted Python code for common issues.
- Reports errors in a teachable format:
  - What went wrong (summary)
  - Why it happened
  - Hints and next steps
  - Optional corrected code
  - Key concepts and optional complexity/best-practice notes
- Supports two feedback modes:
  - Guided mode (default): hints + optional corrected version
  - Diagnostic mode: minimal quick-fix signal without full tutoring extras

## Architecture

- Backend: FastAPI (`/backend`)
- Frontend: Next.js + React (`/frontend`)
- LLM provider: Google Gemini API (used for richer feedback)
- Execution model: Static-only checks in V1 (no server-side code execution)

## Local setup

### Backend

```bash
cd backend
cp .env.example .env
# Add your Gemini key to backend/.env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
# Ensure NEXT_PUBLIC_API_URL points to your backend /api/analyze endpoint
npm install
npm run dev
```

Backend defaults to: `http://127.0.0.1:8000`

Frontend runs at: `http://localhost:3000`

## API contract

`POST /api/analyze`

### Request

```json
{
  "code": "print('hello')",
  "help_mode": "guided",
  "hint_depth": 1,
  "include_complexity": false,
  "include_solution": true
}
```

- `help_mode`: `guided` or `diagnostic`
- `hint_depth`: `1 | 2 | 3` (only meaningful for guided mode)

### Response

```json
{
  "summary": "...",
  "error_clusters": [],
  "hints": [
    { "level": "beginner", "text": "..." }
  ],
  "full_solution": { "code": "...", "explanation": "..." },
  "key_concepts": [],
  "complexity": { "time": "...", "space": "..." },
  "best_practices": []
}
```

## Environment and secrets

The project uses `.env` files for runtime configuration and API keys.

Required runtime values:
- `backend/.env`:
  - `GEMINI_API_KEY`
  - Optional: `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`, `ALLOWED_ORIGINS`, `MAX_CODE_CHARS`
- `frontend/.env.local`:
  - `NEXT_PUBLIC_API_URL`

## Deployment (free hosting path)

This repo is designed for:

- Render: backend API service
- Vercel: frontend web app

### Render backend

1. Use the `render.yaml` file for automatic service setup.
2. Set environment variable `GEMINI_API_KEY` in Render.
3. Set `ALLOWED_ORIGINS` to the Vercel frontend URL.

### Vercel frontend

1. Set project root to `frontend`.
2. Add env var:
   - `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/analyze`


## License

MIT. See `LICENSE`.
