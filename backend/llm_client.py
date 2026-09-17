"""Wraps the Anthropic API for the LLM-driven review pass.

The model is asked to return ONLY a JSON array of findings, which we parse
and merge with the static-analysis results in analyzer.py.
"""
import json
import re
from typing import List

from backend.config import settings
from backend.models import Category, Issue, Severity

SYSTEM_PROMPT = """You are a senior software engineer and application security \
reviewer performing a code review. You will be given a source file, its \
language, and a list of issues an automated static analyzer already found \
(so you should NOT repeat those unless you're adding meaningfully more detail).

Find additional issues a static regex scanner would miss: logic bugs, \
off-by-one errors, race conditions, resource leaks, missing input validation, \
improper error handling, null/undefined handling, unclear or misleading \
naming, poor separation of concerns, performance issues (e.g. O(n^2) where \
O(n) is easy, needless re-computation, N+1 queries), and security issues that \
require understanding context (authz checks, trust boundaries, injection via \
non-obvious sinks, sensitive data exposure).

Respond with ONLY a raw JSON array (no markdown fences, no prose before or \
after) of objects with EXACTLY these keys:
- "category": one of "bug", "security", "code_smell", "performance", "style"
- "severity": one of "critical", "high", "medium", "low", "info"
- "title": short (<=8 words) title
- "description": 1-3 sentences explaining the issue and its real-world impact
- "suggestion": a concrete fix; include a short corrected code snippet if useful
- "line": integer line number if you can identify one, else null

If you find nothing beyond what's already listed, return an empty array [].
Do not invent line numbers you're not reasonably confident about — use null \
instead. Limit yourself to at most 12 of the most important findings."""


def _build_user_prompt(code: str, language: str, static_findings_summary: str) -> str:
    return f"""Language: {language}

Static analyzer already found:
{static_findings_summary or "(none)"}

Source code (line numbers added for reference):
```
{_number_lines(code)}
```"""


def _number_lines(code: str) -> str:
    return "\n".join(f"{i+1:>4}| {line}" for i, line in enumerate(code.splitlines()))


def _extract_json_array(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # Fallback: grab the first [...] block if there's stray prose around it
    if not text.startswith("["):
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)
    return text


def run_llm_review(code: str, language: str, static_findings_summary: str) -> List[Issue]:
    """Calls the Claude API and returns a list of Issue objects.
    Raises on API/parse failure so the caller can decide how to degrade."""
    from anthropic import Anthropic  # imported lazily so static-only mode has no hard dep

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_user_prompt(code, language, static_findings_summary)}
        ],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    raw = "\n".join(text_parts)
    json_text = _extract_json_array(raw)

    try:
        findings = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}\nRaw: {raw[:500]}")

    issues: List[Issue] = []
    for i, f in enumerate(findings):
        try:
            issues.append(
                Issue(
                    id=f"llm-{i+1}",
                    category=Category(f.get("category", "code_smell")),
                    severity=Severity(f.get("severity", "low")),
                    title=f.get("title", "Untitled finding"),
                    description=f.get("description", ""),
                    suggestion=f.get("suggestion", ""),
                    line=f.get("line"),
                    line_snippet=None,
                    source="llm",
                    confidence=0.65,
                )
            )
        except (ValueError, KeyError):
            continue  # skip malformed individual findings rather than failing the whole batch

    return issues
