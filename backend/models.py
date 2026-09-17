"""Shared data models for the code review agent."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    CODE_SMELL = "code_smell"
    PERFORMANCE = "performance"
    STYLE = "style"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Higher = worse. Used for sorting and risk-score math.
SEVERITY_WEIGHT = {
    Severity.CRITICAL: 10,
    Severity.HIGH: 6,
    Severity.MEDIUM: 3,
    Severity.LOW: 1,
    Severity.INFO: 0,
}


class Issue(BaseModel):
    id: str = Field(..., description="Stable identifier, e.g. rule id or llm-<n>")
    category: Category
    severity: Severity
    title: str
    description: str = Field(..., description="Plain-English explanation of the issue and its impact")
    suggestion: str = Field(..., description="Concrete fix or improved code snippet")
    line: Optional[int] = Field(None, description="1-indexed line number, if known")
    line_snippet: Optional[str] = Field(None, description="The offending line of code, if known")
    source: str = Field(..., description="Origin of the finding: 'static' or 'llm'")


class ReviewRequest(BaseModel):
    code: str
    filename: str = "snippet.txt"
    language: Optional[str] = None  # auto-detected if omitted


class Metrics(BaseModel):
    lines_of_code: int
    blank_lines: int
    comment_lines: int
    comment_ratio: float
    function_count: int
    longest_function_lines: int
    approx_cyclomatic_complexity: int
    max_nesting_depth: int


class Summary(BaseModel):
    total_issues: int
    by_severity: dict
    by_category: dict
    risk_score: int = Field(..., description="0-100, higher = riskier")
    verdict: str


class ReviewReport(BaseModel):
    filename: str
    language: str
    issues: List[Issue]
    metrics: Metrics
    summary: Summary
    llm_used: bool
    cached: bool = False
