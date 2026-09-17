"""Core hybrid analysis engine.

Pipeline:
  1. detect language
  2. run static rule engine -> deterministic Issues
  3. compute metrics (complexity, comment ratio, etc.) -> smell-based Issues too
  4. if enabled & available, run LLM pass for deeper/contextual Issues
  5. merge, dedupe, sort, score -> ReviewReport
"""
import logging
from typing import List

from backend.cache import review_cache
from backend.config import settings
from backend.language import detect_language
from backend.llm_client import run_llm_review
from backend.metrics import compute_metrics
from backend.models import (
    Category,
    Issue,
    Metrics,
    ReviewReport,
    Severity,
    Summary,
    SEVERITY_WEIGHT,
)
from backend.static_rules import get_rules_for_language, line_number_for_match, line_text

logger = logging.getLogger("analyzer")


def _run_static_rules(code: str, language: str) -> List[Issue]:
    issues: List[Issue] = []
    for rule in get_rules_for_language(language):
        for match in rule.pattern.finditer(code):
            line_no = line_number_for_match(code, match.start())
            issues.append(
                Issue(
                    id=rule.id,
                    category=rule.category,
                    severity=rule.severity,
                    title=rule.title,
                    description=rule.description,
                    suggestion=rule.suggestion,
                    line=line_no,
                    line_snippet=line_text(code, line_no),
                    source="static",
                )
            )
    return issues


def _metric_based_smells(metrics: Metrics) -> List[Issue]:
    issues: List[Issue] = []
    if metrics.longest_function_lines > 60:
        issues.append(
            Issue(
                id="METRIC-LONG-FN",
                category=Category.CODE_SMELL,
                severity=Severity.MEDIUM,
                title="Very long function",
                description=(
                    f"At least one function spans roughly {metrics.longest_function_lines} lines. "
                    "Long functions are harder to test, reason about, and reuse."
                ),
                suggestion="Extract cohesive chunks of logic into smaller, well-named helper functions.",
                line=None,
                line_snippet=None,
                source="static",
            )
        )
    if metrics.max_nesting_depth > 4:
        issues.append(
            Issue(
                id="METRIC-DEEP-NEST",
                category=Category.CODE_SMELL,
                severity=Severity.LOW,
                title="Deep nesting",
                description=(
                    f"Nesting depth of roughly {metrics.max_nesting_depth} makes control flow "
                    "hard to follow and increases the chance of logic errors."
                ),
                suggestion="Use early returns/guard clauses, or extract nested blocks into functions.",
                line=None,
                line_snippet=None,
                source="static",
            )
        )
    if metrics.approx_cyclomatic_complexity > 20:
        issues.append(
            Issue(
                id="METRIC-HIGH-COMPLEXITY",
                category=Category.CODE_SMELL,
                severity=Severity.MEDIUM,
                title="High cyclomatic complexity",
                description=(
                    f"Approximate cyclomatic complexity is {metrics.approx_cyclomatic_complexity}, "
                    "indicating many independent code paths in this file, which raises test burden "
                    "and defect risk."
                ),
                suggestion="Split branching logic into smaller functions or use polymorphism/lookup "
                "tables instead of long if/elif chains.",
                line=None,
                line_snippet=None,
                source="static",
            )
        )
    if metrics.lines_of_code > 20 and metrics.comment_ratio < 0.03:
        issues.append(
            Issue(
                id="METRIC-LOW-COMMENTS",
                category=Category.CODE_SMELL,
                severity=Severity.INFO,
                title="Very low comment density",
                description="Almost no comments/docstrings were found, which can make intent and "
                "edge-case handling hard for future maintainers to infer.",
                suggestion="Add docstrings for public functions and comments for non-obvious logic.",
                line=None,
                line_snippet=None,
                source="static",
            )
        )
    return issues


def _summarize_static_for_prompt(issues: List[Issue]) -> str:
    if not issues:
        return ""
    lines = []
    for issue in issues[:20]:
        loc = f"line {issue.line}" if issue.line else "unknown line"
        lines.append(f"- [{issue.severity.value}/{issue.category.value}] {issue.title} ({loc})")
    return "\n".join(lines)


def _dedupe(issues: List[Issue]) -> List[Issue]:
    seen = set()
    unique = []
    for issue in issues:
        key = (issue.category, issue.line, issue.title.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique


def _compute_summary(issues: List[Issue], metrics: Metrics) -> Summary:
    by_severity = {s.value: 0 for s in Severity}
    by_category = {c.value: 0 for c in Category}
    for issue in issues:
        by_severity[issue.severity.value] += 1
        by_category[issue.category.value] += 1

    raw_score = sum(SEVERITY_WEIGHT[i.severity] for i in issues)
    # Normalize into a 0-100 risk score with diminishing returns for very long lists
    risk_score = min(100, round(100 * (1 - pow(0.92, raw_score))))

    if by_severity[Severity.CRITICAL.value] > 0:
        verdict = "Do not merge — critical issue(s) must be fixed first."
    elif by_severity[Severity.HIGH.value] > 0:
        verdict = "Needs changes before merging — high-severity issue(s) found."
    elif by_severity[Severity.MEDIUM.value] > 2:
        verdict = "Reviewable, but several medium-severity issues should be addressed."
    elif issues:
        verdict = "Looks mergeable — only minor issues found."
    else:
        verdict = "No issues detected."

    return Summary(
        total_issues=len(issues),
        by_severity=by_severity,
        by_category=by_category,
        risk_score=risk_score,
        verdict=verdict,
    )


def review_code(code: str, filename: str = "snippet.txt", language: str = None) -> ReviewReport:
    if not code or not code.strip():
        raise ValueError("No code provided.")

    max_bytes = settings.MAX_FILE_SIZE_KB * 1024
    if len(code.encode("utf-8")) > max_bytes:
        raise ValueError(f"File exceeds max size of {settings.MAX_FILE_SIZE_KB} KB.")

    lang = language or detect_language(filename, code)

    cache_key = review_cache.make_key(code, filename, lang, settings.ANTHROPIC_MODEL)
    cached = review_cache.get(cache_key)
    if cached is not None:
        # Return a copy so mutating `.cached` here never affects the cached
        # original or any previously-returned report object.
        hit = cached.model_copy()
        hit.cached = True
        return hit

    static_issues = _run_static_rules(code, lang)
    metrics = compute_metrics(code)
    static_issues += _metric_based_smells(metrics)

    llm_used = False
    llm_issues: List[Issue] = []
    if settings.llm_available:
        try:
            llm_issues = run_llm_review(code, lang, _summarize_static_for_prompt(static_issues))
            llm_used = True
        except Exception as e:  # degrade gracefully — static results are still useful
            logger.warning("LLM review pass failed, falling back to static-only: %s", e)

    all_issues = _dedupe(static_issues + llm_issues)
    all_issues.sort(key=lambda i: (-SEVERITY_WEIGHT[i.severity], i.line or 0))

    summary = _compute_summary(all_issues, metrics)

    report = ReviewReport(
        filename=filename,
        language=lang,
        issues=all_issues,
        metrics=metrics,
        summary=summary,
        llm_used=llm_used,
        cached=False,
    )
    review_cache.set(cache_key, report)
    return report
