import ast
from typing import Any, Dict

from .llm import generate_feedback
from .models import AnalyzeResponse
from .static_checks import run_static_checks


def _normalize_clusters(clusters: list[dict]) -> list[dict]:
    for cluster in clusters:
        if cluster.get("type") == "NameError":
            cluster["type"] = "Potential issue"
    return clusters


def analyze_python_code(
    code: str,
    hint_level: int,
    help_mode: str,
    include_complexity: bool,
    include_solution: bool,
) -> Dict[str, Any]:
    source = (code or "").strip()
    if not source:
        return AnalyzeResponse(
            summary="No code provided. Paste Python code first.",
            error_clusters=[],
            hints=[],
            key_concepts=["Code entry point", "Begin by writing one valid statement"],
            best_practices=["Start with small, runnable snippets."],
            full_solution=None,
        ).model_dump()

    issues = []
    syntax_ok = True
    tree = None

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        syntax_ok = False
        issues.append(
            {
                "type": "SyntaxError",
                "line": exc.lineno or 0,
                "snippet": exc.text.strip() if exc.text else None,
                "why": exc.msg,
                "severity": "error",
            }
        )

    static_context = {"issues": [], "complexity": None}
    if syntax_ok and tree is not None:
        static_context = run_static_checks(source)
        issues = static_context.get("issues", [])
        if not issues:
            issues = []

    complexity = static_context.get("complexity")
    if not include_complexity:
        complexity = None

    feedback = generate_feedback(
        source,
        issues,
        hint_level=hint_level,
        include_complexity=include_complexity,
        include_solution=include_solution and help_mode == "guided",
        complexity=complexity,
    )

    if help_mode == "diagnostic":
        # People in diagnostic mode want quick checks, not guided tutoring.
        feedback["hints"] = []
        feedback["full_solution"] = None
        feedback.pop("best_practices", None)
        feedback.pop("key_concepts", None)

    # Keep static issues the source of truth. If model returns different clusters, merge safely.
    response = AnalyzeResponse(
        summary=feedback.get("summary", "Analysis completed."),
        error_clusters=_normalize_clusters(issues if issues else feedback.get("error_clusters", [])),
        hints=feedback.get("hints", []),
        full_solution=feedback.get("full_solution"),
        key_concepts=feedback.get("key_concepts", []),
        complexity=feedback.get("complexity") if include_complexity else None,
        best_practices=feedback.get("best_practices", []),
    )
    return response.model_dump()
