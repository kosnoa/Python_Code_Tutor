import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from analyzer.analyzer import analyze_python_code
from analyzer.models import AnalyzeRequest

load_dotenv()


app = FastAPI(title="AI-Assisted Python Feedback API", version="0.1.0")

allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allow_list = [origin.strip() for origin in allowed.split(",") if origin.strip()]
if not allow_list:
    allow_list = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> JSONResponse:
    max_chars = int(os.getenv("MAX_CODE_CHARS", "20000"))
    if len(payload.code) > max_chars:
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"Code too large. Max allowed characters is {max_chars}.",
            },
        )

    result = analyze_python_code(
        code=payload.code,
        hint_level=payload.hint_depth or payload.hint_level or 1,
        help_mode=payload.help_mode,
        include_complexity=payload.include_complexity,
        include_solution=payload.include_solution,
    )
    return JSONResponse(content=result)
