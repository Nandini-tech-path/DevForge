"""
Deterministic, regex/heuristic based static analysis rules.

These are intentionally conservative (favor precision over recall) since
false positives here are shown to the user with no LLM judgment attached.
Each rule is (rule_id, category, severity, title, pattern, description, suggestion).

Language keys: "python", "javascript", "java", "go", "c", "generic".
"generic" rules run against every language in addition to language-specific ones.
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from backend.models import Category, Severity


@dataclass
class Rule:
    id: str
    category: Category
    severity: Severity
    title: str
    pattern: re.Pattern
    description: str
    suggestion: str


def _r(pattern: str, flags=re.IGNORECASE) -> re.Pattern:
    return re.compile(pattern, flags)


PYTHON_RULES: List[Rule] = [
    Rule(
        "PY-SEC-001", Category.SECURITY, Severity.CRITICAL, "Use of eval()/exec()",
        _r(r"\b(eval|exec)\s*\("),
        "eval()/exec() run arbitrary strings as code. If any part of the input can be "
        "influenced by a user, this is a remote code execution vulnerability.",
        "Avoid eval/exec entirely. Use ast.literal_eval() for safe literal parsing, or "
        "a proper parser/dispatch table for dynamic behavior.",
    ),
    Rule(
        "PY-SEC-002", Category.SECURITY, Severity.CRITICAL, "Shell injection via subprocess/os.system",
        _r(r"(os\.system\s*\(|subprocess\.(call|run|Popen|check_output)\([^)]*shell\s*=\s*True)"),
        "Passing shell=True (or using os.system) with any interpolated/user-controlled "
        "string allows arbitrary command execution.",
        "Use subprocess.run([...], shell=False) with an argument list, and never "
        "interpolate untrusted input into a shell string.",
    ),
    Rule(
        "PY-SEC-003", Category.SECURITY, Severity.HIGH, "Insecure deserialization (pickle/yaml)",
        _r(r"(pickle\.load[s]?\s*\(|yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader))"),
        "pickle.load and yaml.load (without SafeLoader) can execute arbitrary code when "
        "deserializing untrusted data.",
        "Use yaml.safe_load() for YAML. Avoid pickle for untrusted data entirely; use "
        "json or a schema-validated format instead.",
    ),
    Rule(
        "PY-SEC-004", Category.SECURITY, Severity.HIGH, "SQL query built via string formatting",
        _r(r"(execute|executemany)\s*\(\s*(f[\"']|[\"'].*%s.*[\"']\s*%|[\"'].*\+.*[\"'])"),
        "Building SQL with f-strings, % formatting, or concatenation allows SQL injection "
        "if any part of the string comes from user input.",
        "Use parameterized queries, e.g. cursor.execute('SELECT * FROM t WHERE id = %s', (id,)).",
    ),
    Rule(
        "PY-SEC-005", Category.SECURITY, Severity.HIGH, "Hardcoded secret/credential",
        _r(r"(?:api[_-]?key|secret|password|passwd|token)\s*=\s*[\"'][A-Za-z0-9_\-/+=]{8,}[\"']"),
        "Hardcoding credentials in source code means they end up in version control and "
        "are visible to anyone with repo access.",
        "Load secrets from environment variables or a secrets manager (e.g. os.environ, "
        "AWS Secrets Manager, Vault) and never commit them.",
    ),
    Rule(
        "PY-SEC-006", Category.SECURITY, Severity.MEDIUM, "Weak hash algorithm for sensitive data",
        _r(r"hashlib\.(md5|sha1)\s*\("),
        "MD5 and SHA-1 are cryptographically broken and unsuitable for passwords, "
        "signatures, or integrity checks against adversarial input.",
        "Use hashlib.sha256 or better for integrity checks, and a dedicated password "
        "hashing scheme (bcrypt, scrypt, argon2) for credentials.",
    ),
    Rule(
        "PY-SEC-007", Category.SECURITY, Severity.MEDIUM, "Insecure random for security purposes",
        _r(r"\brandom\.(random|randint|choice)\s*\("),
        "The `random` module is not cryptographically secure and is predictable, which "
        "is unsafe for tokens, passwords, or any security-sensitive value.",
        "Use the `secrets` module (e.g. secrets.token_urlsafe()) for anything "
        "security-related.",
    ),
    Rule(
        "PY-SEC-008", Category.SECURITY, Severity.HIGH, "Debug mode enabled",
        _r(r"debug\s*=\s*True"),
        "Running with debug=True in frameworks like Flask/Django can leak stack traces, "
        "source code, and environment variables to attackers in production.",
        "Set debug mode from an environment variable and default to False.",
    ),
    Rule(
        "PY-BUG-001", Category.BUG, Severity.MEDIUM, "Bare except clause",
        _r(r"except\s*:\s*$", flags=re.MULTILINE),
        "A bare `except:` silently swallows all exceptions, including KeyboardInterrupt "
        "and SystemExit, and hides real bugs.",
        "Catch specific exception types, e.g. `except (ValueError, KeyError) as e:`.",
    ),
    Rule(
        "PY-BUG-002", Category.BUG, Severity.HIGH, "Mutable default argument",
        _r(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|\(\))[^)]*\)\s*:"),
        "Mutable default arguments (list/dict/set) are created once and shared across "
        "all calls, causing subtle state-leak bugs.",
        "Use `None` as the default and initialize the mutable value inside the function body.",
    ),
    Rule(
        "PY-BUG-003", Category.BUG, Severity.LOW, "Comparing to None with == instead of is",
        _r(r"==\s*None|!=\s*None"),
        "`== None` invokes __eq__ and can behave unexpectedly with custom classes; "
        "identity comparison is the Pythonic and correct approach.",
        "Use `is None` / `is not None`.",
    ),
]

JAVASCRIPT_RULES: List[Rule] = [
    Rule(
        "JS-SEC-001", Category.SECURITY, Severity.CRITICAL, "Use of eval() or new Function()",
        _r(r"\beval\s*\(|new\s+Function\s*\("),
        "eval()/Function() execute arbitrary strings as code — classic RCE/XSS vector "
        "if any input is attacker-influenced.",
        "Avoid eval entirely. Use JSON.parse for data, and explicit dispatch for logic.",
    ),
    Rule(
        "JS-SEC-002", Category.SECURITY, Severity.HIGH, "innerHTML/outerHTML assignment (XSS risk)",
        _r(r"\.(innerHTML|outerHTML)\s*="),
        "Assigning untrusted data to innerHTML lets an attacker inject arbitrary "
        "HTML/JavaScript (stored/reflected XSS).",
        "Use textContent for plain text, or sanitize with a library like DOMPurify "
        "before inserting HTML.",
    ),
    Rule(
        "JS-SEC-003", Category.SECURITY, Severity.HIGH, "Hardcoded secret/credential",
        _r(r"(?:apiKey|secret|password|token)\s*[:=]\s*[\"'][A-Za-z0-9_\-/+=]{8,}[\"']"),
        "Hardcoded credentials in source ship straight to version control and, for "
        "frontend code, to every client's browser.",
        "Load secrets from environment variables (server-side) and never embed them "
        "in client-side bundles.",
    ),
    Rule(
        "JS-SEC-004", Category.SECURITY, Severity.MEDIUM, "Wildcard CORS",
        _r(r"Access-Control-Allow-Origin[\"']?\s*[:,]\s*[\"']\*[\"']"),
        "A wildcard CORS origin allows any website to make authenticated requests to "
        "this API from a victim's browser.",
        "Restrict Access-Control-Allow-Origin to a specific allow-list of trusted origins.",
    ),
    Rule(
        "JS-BUG-001", Category.BUG, Severity.MEDIUM, "Loose equality (== / !=)",
        _r(r"[^=!]==[^=]|!=[^=]"),
        "Loose equality performs type coercion that frequently causes surprising bugs "
        "(e.g. '' == 0 is true).",
        "Use strict equality `===` / `!==` unless coercion is explicitly intended.",
    ),
    Rule(
        "JS-BUG-002", Category.BUG, Severity.LOW, "console.log left in code",
        _r(r"console\.(log|debug)\s*\("),
        "Leftover debug logging clutters production output and can leak internal data.",
        "Remove debug logs or replace with a proper logger that respects log levels.",
    ),
    Rule(
        "JS-SMELL-001", Category.CODE_SMELL, Severity.LOW, "var used instead of let/const",
        _r(r"\bvar\s+\w+"),
        "`var` is function-scoped and hoisted, which is a common source of confusing "
        "bugs compared to block-scoped let/const.",
        "Use `const` by default, `let` when reassignment is needed.",
    ),
]

JAVA_RULES: List[Rule] = [
    Rule(
        "JAVA-SEC-001", Category.SECURITY, Severity.HIGH, "SQL built via string concatenation",
        _r(r"(Statement\b(?!.*Prepared)).*executeQuery\s*\(\s*\".*\"\s*\+"),
        "Concatenating strings into a SQL query allows SQL injection.",
        "Use PreparedStatement with bound parameters instead of Statement + concatenation.",
    ),
    Rule(
        "JAVA-SEC-002", Category.SECURITY, Severity.MEDIUM, "Weak hash algorithm",
        _r(r"MessageDigest\.getInstance\s*\(\s*[\"'](MD5|SHA-1)[\"']"),
        "MD5/SHA-1 are broken for security purposes such as integrity or password hashing.",
        "Use SHA-256 or a dedicated password hashing library (bcrypt/argon2).",
    ),
    Rule(
        "JAVA-BUG-001", Category.BUG, Severity.MEDIUM, "Empty catch block",
        _r(r"catch\s*\([^)]*\)\s*\{\s*\}"),
        "Swallowing exceptions silently hides failures and makes debugging much harder.",
        "At minimum log the exception; better, handle it or rethrow a wrapped exception.",
    ),
]

GO_RULES: List[Rule] = [
    Rule(
        "GO-SEC-001", Category.SECURITY, Severity.HIGH, "Command built with exec.Command from untrusted input",
        _r(r"exec\.Command\s*\("),
        "If any argument comes from user input, this can lead to command injection "
        "depending on how it's constructed.",
        "Validate/allow-list inputs, and avoid passing a shell interpreter; pass "
        "arguments as a slice, never as a concatenated shell string.",
    ),
]

GENERIC_RULES: List[Rule] = [
    Rule(
        "GEN-SMELL-001", Category.CODE_SMELL, Severity.INFO, "TODO/FIXME left in code",
        _r(r"#\s*(TODO|FIXME)|//\s*(TODO|FIXME)"),
        "Unresolved TODO/FIXME markers often indicate known gaps or temporary hacks.",
        "Track these in an issue tracker and resolve or remove before merging.",
    ),
    Rule(
        "GEN-SEC-001", Category.SECURITY, Severity.HIGH, "Hardcoded private key / PEM block",
        _r(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "A private key committed to source control is compromised the moment it's pushed "
        "and must be treated as leaked.",
        "Remove the key, rotate/revoke it immediately, and load keys from a secrets "
        "manager or mounted secret volume.",
    ),
]

RULES_BY_LANGUAGE = {
    "python": PYTHON_RULES,
    "javascript": JAVASCRIPT_RULES,
    "typescript": JAVASCRIPT_RULES,
    "java": JAVA_RULES,
    "go": GO_RULES,
}


def get_rules_for_language(language: str) -> List[Rule]:
    return RULES_BY_LANGUAGE.get(language, []) + GENERIC_RULES


def line_number_for_match(code: str, match_start: int) -> int:
    return code.count("\n", 0, match_start) + 1


def line_text(code: str, line_no: int) -> Optional[str]:
    lines = code.splitlines()
    if 1 <= line_no <= len(lines):
        return lines[line_no - 1].strip()
    return None
