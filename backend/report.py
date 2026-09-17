"""Renders a ReviewReport into Markdown (for humans/PRs) or JSON (for tooling)."""
import json

from backend.models import ReviewReport

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def to_json(report: ReviewReport) -> str:
    return report.model_dump_json(indent=2)


def to_markdown(report: ReviewReport) -> str:
    s = report.summary
    lines = [
        f"# Code Review: `{report.filename}`",
        "",
        f"**Language:** {report.language}  ",
        f"**Risk score:** {s.risk_score}/100  ",
        f"**Verdict:** {s.verdict}  ",
        f"**Analysis mode:** {'hybrid (static + LLM)' if report.llm_used else 'static rules only'}",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|---|---|",
    ]
    for sev, count in s.by_severity.items():
        if count:
            lines.append(f"| {SEVERITY_EMOJI.get(sev, '')} {sev} | {count} |")

    lines += ["", "| Category | Count |", "|---|---|"]
    for cat, count in s.by_category.items():
        if count:
            lines.append(f"| {cat} | {count} |")

    lines += ["", "## Metrics", ""]
    m = report.metrics
    lines += [
        f"- Lines of code: {m.lines_of_code}",
        f"- Comment ratio: {m.comment_ratio * 100:.1f}%",
        f"- Functions detected: {m.function_count}",
        f"- Longest function (approx. lines): {m.longest_function_lines}",
        f"- Approx. cyclomatic complexity: {m.approx_cyclomatic_complexity}",
        f"- Max nesting depth: {m.max_nesting_depth}",
        "",
        "## Findings",
        "",
    ]

    if not report.issues:
        lines.append("No issues found. ✅")
    else:
        for issue in report.issues:
            loc = f" (line {issue.line})" if issue.line else ""
            lines.append(
                f"### {SEVERITY_EMOJI.get(issue.severity.value, '')} "
                f"[{issue.severity.value.upper()}] {issue.title}{loc}"
            )
            lines.append(f"*Category: {issue.category.value} · Source: {issue.source} · Rule: `{issue.id}`*")
            metadata = [f"Confidence: {issue.confidence:.0%}"]
            if issue.cwe:
                metadata.append(f"CWE: {issue.cwe}")
            lines.append(f"*{' · '.join(metadata)}*")
            lines.append("")
            lines.append(f"**Why it matters:** {issue.description}")
            lines.append("")
            lines.append(f"**Suggested fix:** {issue.suggestion}")
            if issue.line_snippet:
                lines.append("")
                lines.append(f"```\n{issue.line_snippet}\n```")
            lines.append("")

    return "\n".join(lines)
