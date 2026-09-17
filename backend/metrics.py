"""Lightweight, language-agnostic code metrics (no AST dependency required,
so it works uniformly across Python/JS/Java/Go/etc.)."""
import re

from backend.models import Metrics

DECISION_KEYWORDS = re.compile(
    r"\b(if|elif|else if|for|while|case|catch|except|foreach)\b|(\&\&|\|\|)"
)
COMMENT_PATTERNS = [
    re.compile(r"^\s*#"),          # python/shell
    re.compile(r"^\s*//"),         # c-style single line
    re.compile(r"^\s*\*"),         # inside block comments
    re.compile(r"^\s*/\*"),
]
FUNCTION_START = re.compile(
    r"^\s*(def\s+\w+\s*\(|function\s+\w*\s*\(|\w+\s*\([^)]*\)\s*\{|"
    r"(public|private|protected|static|\s)*[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{|"
    r"func\s+\w+\s*\()"
)


def _is_comment(line: str) -> bool:
    stripped = line.strip()
    return any(p.match(stripped) for p in COMMENT_PATTERNS)


def compute_metrics(code: str) -> Metrics:
    lines = code.splitlines()
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comments = sum(1 for l in lines if _is_comment(l))
    code_lines = max(total - blank - comments, 0)
    comment_ratio = round(comments / total, 3) if total else 0.0

    complexity = 1 + len(DECISION_KEYWORDS.findall(code))

    # Nesting depth via brace/indent heuristic
    max_depth = 0
    depth = 0
    for line in lines:
        depth += line.count("{") - line.count("}")
        # Python-style indentation as a rough proxy when braces aren't used
        max_depth = max(max_depth, depth)

    indent_depths = []
    for line in lines:
        if line.strip():
            leading = len(line) - len(line.lstrip(" "))
            indent_depths.append(leading // 4)
    indent_max = max(indent_depths) if indent_depths else 0
    max_nesting_depth = max(max_depth, indent_max)

    # Function detection & longest function (line-count) heuristic
    starts = [i for i, l in enumerate(lines) if FUNCTION_START.match(l)]
    longest = 0
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else total
        longest = max(longest, end - start)

    return Metrics(
        lines_of_code=code_lines,
        blank_lines=blank,
        comment_lines=comments,
        comment_ratio=comment_ratio,
        function_count=len(starts),
        longest_function_lines=longest,
        approx_cyclomatic_complexity=complexity,
        max_nesting_depth=max_nesting_depth,
    )
