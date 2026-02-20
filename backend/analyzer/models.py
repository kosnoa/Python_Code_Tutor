from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ErrorCluster(BaseModel):
    type: str = Field(description="Short label like SyntaxError, RuntimeError, Potential issue")
    line: Optional[int] = Field(default=None, description="1-based source line")
    snippet: Optional[str] = Field(default=None, description="Short code snippet where issue appears")
    why: str = Field(description="Beginner-friendly explanation")
    severity: Literal["error", "warning", "info"] = "warning"


class Hint(BaseModel):
    level: Literal["beginner", "intermediate", "near_solution"]
    text: str


class CorrectedCode(BaseModel):
    code: str
    explanation: str


class Complexity(BaseModel):
    time: str
    space: str


class AnalyzeRequest(BaseModel):
    code: str
    # "help_mode" is the user-facing operation.
    # - guided: full support flow with hints + optional corrected code
    # - diagnostic: fast diagnostic checks only
    help_mode: Literal["guided", "diagnostic"] = "guided"
    # "hint_depth" replaces the old hint_level naming.
    hint_depth: Optional[int] = Field(default=None, ge=1, le=3)
    # Backward-compatible alias if older clients still send hint_level.
    hint_level: Optional[int] = Field(default=None, ge=1, le=3)
    include_complexity: bool = False
    include_solution: bool = False


class AnalyzeResponse(BaseModel):
    summary: str
    error_clusters: List[ErrorCluster]
    hints: List[Hint]
    full_solution: Optional[CorrectedCode] = None
    key_concepts: List[str]
    complexity: Optional[Complexity] = None
    best_practices: List[str]
