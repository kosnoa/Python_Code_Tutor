import json
import os
import re
from typing import Any, Dict, List, Optional

import requests

from .models import Hint


def _extract_json(payload_text: str) -> Optional[Dict[str, Any]]:
    if not payload_text:
        return None
    # The model may wrap JSON in a markdown fence.
    fence_match = re.search(r"```json(.*?)```", payload_text, re.DOTALL | re.IGNORECASE)
    candidate = fence_match.group(1).strip() if fence_match else payload_text.strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        return None
    candidate = candidate[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _call_gemini(prompt: str) -> Optional[str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_YOUR_GEMINI_API_KEY_HERE":
        return None

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    timeout = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.95,
            "topK": 40,
        },
    }

    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code != 200:
            return None
        response_data = r.json()
        candidates = response_data.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        return str(parts[0].get("text", ""))
    except Exception:
        return None


def _default_hints_from_issues(issues: List[Dict[str, Any]], hint_level: int) -> List[Hint]:
    max_level = max(1, min(3, hint_level))
    hints: List[Hint] = [
        Hint(
            level="beginner",
            text="Read each red line carefully from the message, then fix one issue at a time before moving on.",
        )
    ]

    if max_level >= 2:
        hints.append(
            Hint(
                level="intermediate",
                text=(
                    "Trace variable values around the failing line. "
                    "If an error says 'undefined' or 'not iterable', print variable types and values before the line."
                ),
            )
        )

    if max_level >= 3:
        hints.append(
            Hint(
                level="near_solution",
                text=(
                    "Consider rewriting the section with guard clauses (early checks like type or range checks) "
                    "to prevent the error conditions before the operation."
                ),
            )
        )

    if not issues:
        hints.append(
            Hint(
                level="beginner",
                text="No static issues found; run a few simple test inputs in class and compare expected outputs.",
            )
        )
    return hints


def build_fallback_response(
    source_code: str,
    issues: List[Dict[str, Any]],
    hint_level: int,
    include_complexity: bool,
    include_solution: bool,
    complexity: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    del source_code  # reserved for future expansion
    summary = "No obvious syntax/runtime risks found in the static checks."
    if issues:
        summary = f"Found {len(issues)} issue(s) to fix before this code is safe to run."

    response: Dict[str, Any] = {
        "summary": summary,
        "error_clusters": issues,
        "hints": [h.model_dump() for h in _default_hints_from_issues(issues, hint_level)],
        "key_concepts": [
            "Reading traceback-like errors",
            "Guarding edge cases before math or indexing",
            "Checking variable scope and definitions",
        ],
        "best_practices": [
            "Use clear variable names and consistent indentation.",
            "Handle edge cases (empty lists, zero division, wrong types) explicitly.",
            "Add one simple test input for each branch of logic.",
        ],
    }

    if include_complexity and complexity is not None:
        response["complexity"] = complexity

    if include_solution:
        response["full_solution"] = {
            "code": "",
            "explanation": (
                "No Gemini key is configured right now. Add your Google AI Studio key to backend/.env "
                "to get an improved code version and deeper teaching hints."
            ),
        }
    return response


def generate_feedback(
    code: str,
    issues: List[Dict[str, Any]],
    hint_level: int,
    include_complexity: bool,
    include_solution: bool,
    complexity: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    schema_example = """
{
  \"summary\": \"What went wrong in plain English.\",
  \"error_clusters\": [
    {\"type\":\"...\", \"line\": 1, \"snippet\":\"...\", \"why\":\"...\", \"severity\":\"error|warning|info\"}
  ],
  \"hints\": [
    {\"level\":\"beginner\",\"text\":\"...\"},
    {\"level\":\"intermediate\",\"text\":\"...\"},
    {\"level\":\"near_solution\",\"text\":\"...\"}
  ],
  \"full_solution\": {\"code\":\"...\", \"explanation\":\"...\"},
  \"key_concepts\": [\"...\"],
  \"complexity\": {\"time\":\"...\", \"space\":\"...\"},
  \"best_practices\": [\"...\"]
}
"""

    prompt = (
        "You are a Python tutor for beginners. Produce strict JSON only with this schema:\n"
        f"{schema_example}\n"
        "Rules:\n"
        "1) Keep all explanations beginner-friendly.\n"
        "2) If include_complexity is false, omit complexity from the response.\n"
        "3) If include_solution is false, omit full_solution from the response.\n"
        "4) Include at most 5 hints total. Keep them practical and specific.\n"
        "5) If the code has no issues, return a supportive summary and include 1-2 positive hints.\n\n"
        "Input metadata:\n"
        f"- hint_depth: {hint_level}\n"
        f"- include_complexity: {include_complexity}\n"
        f"- include_solution: {include_solution}\n\n"
        f"Static issues already found:\n{issues}\n\n"
        "Use this code:\n"
        "```python\n"
        f"{code}\n"
        "```"
    )

    raw = _call_gemini(prompt)
    parsed = _extract_json(raw) if raw else None

    if not parsed:
        return build_fallback_response(code, issues, hint_level, include_complexity, include_solution, complexity)

    result: Dict[str, Any] = {
        "summary": parsed.get("summary", "No clear message from tutor model."),
        "error_clusters": parsed.get("error_clusters", issues),
        "hints": parsed.get("hints", [h.model_dump() for h in _default_hints_from_issues(issues, hint_level)]),
        "key_concepts": parsed.get("key_concepts", []),
        "best_practices": parsed.get("best_practices", []),
    }

    if include_complexity and parsed.get("complexity") is not None:
        result["complexity"] = parsed["complexity"]
    if include_solution and parsed.get("full_solution") is not None:
        result["full_solution"] = parsed["full_solution"]
    if include_solution and "full_solution" not in result and "full_solution" not in parsed:
        result["full_solution"] = {
            "code": "",
            "explanation": "Solver did not return a corrected version.",
        }
    return result
