"""
Unit tests for the static-analysis layer (LLM pass is mocked/disabled so these
run offline and deterministically, e.g. in CI without an API key).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings

settings.ENABLE_LLM_REVIEW = False  # force static-only mode for deterministic tests

from backend.analyzer import review_code  # noqa: E402
from backend.language import detect_language  # noqa: E402
from backend.metrics import compute_metrics  # noqa: E402


def test_detect_language_by_extension():
    assert detect_language("app.py", "") == "python"
    assert detect_language("app.js", "") == "javascript"
    assert detect_language("app.go", "") == "go"
    assert detect_language("unknown.xyz", "def foo(): pass") == "python"


def test_detects_eval_as_critical_security_issue():
    report = review_code("x = eval(user_input)\n", "snippet.py")
    ids = [i.id for i in report.issues]
    assert "PY-SEC-001" in ids
    issue = next(i for i in report.issues if i.id == "PY-SEC-001")
    assert issue.severity.value == "critical"
    assert issue.category.value == "security"


def test_detects_hardcoded_secret():
    code = 'api_key = "abcd1234efgh5678"\n'
    report = review_code(code, "config.py")
    assert any(i.id == "PY-SEC-005" for i in report.issues)


def test_detects_mutable_default_argument():
    code = "def f(items=[]):\n    return items\n"
    report = review_code(code, "utils.py")
    assert any(i.id == "PY-BUG-002" for i in report.issues)


def test_detects_bare_except():
    code = "try:\n    do_thing()\nexcept:\n    pass\n"
    report = review_code(code, "utils.py")
    assert any(i.id == "PY-BUG-001" for i in report.issues)


def test_clean_code_produces_no_issues():
    code = (
        "def add(a: int, b: int) -> int:\n"
        "    \"\"\"Return the sum of two integers.\"\"\"\n"
        "    return a + b\n"
    )
    report = review_code(code, "math_utils.py")
    assert report.summary.total_issues == 0
    assert report.summary.risk_score == 0


def test_risk_score_increases_with_severity():
    low_risk = review_code("x = 1\n", "a.py")
    high_risk = review_code("os.system('rm -rf ' + user_input)\n", "b.py")
    assert high_risk.summary.risk_score > low_risk.summary.risk_score


def test_metrics_flag_long_function():
    long_body = "\n".join(f"    x{i} = {i}" for i in range(80))
    code = f"def big_function():\n{long_body}\n    return x0\n"
    metrics = compute_metrics(code)
    assert metrics.longest_function_lines > 60


def test_empty_code_raises():
    import pytest

    with pytest.raises(ValueError):
        review_code("   ", "empty.py")


def test_cache_returns_cached_flag_on_second_call():
    code = "def f():\n    return 1\n"
    first = review_code(code, "cache_test.py")
    second = review_code(code, "cache_test.py")
    assert first.cached is False
    assert second.cached is True
