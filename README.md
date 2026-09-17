# AI Code Review & Vulnerability Detection Agent

An AI-powered code review assistant that analyzes source code for **bugs**,
**security vulnerabilities**, and **code smells**, classifies each finding by
**severity**, explains *why* it matters, and suggests a concrete fix.

It works as a **hybrid analyzer**:

1. **Static rule engine** — fast, deterministic regex/heuristic checks for
   well-known vulnerability and anti-pattern classes (SQLi, command injection,
   hardcoded secrets, insecure deserialization, weak crypto, etc.) across
   several languages.
2. **LLM review pass (Claude)** — reads the code plus the static findings and
   produces deeper, context-aware findings (logic bugs, race conditions,
   missing validation, unclear naming, poor error handling, etc.) that regex
   alone can't catch, and writes human explanations + fixes for everything.
3. **Metrics engine** — lines of code, comment ratio, approximate cyclomatic
   complexity, longest function, risk score.

The two passes are merged, de-duplicated, and returned as a single structured
report (JSON + Markdown).

---

## Features

- 🐛 Bug detection (null checks, off-by-one, unhandled exceptions, resource
  leaks, race conditions, logic errors)
- 🔒 Security vulnerability detection (OWASP-style: injection, XSS, insecure
  deserialization, hardcoded secrets, weak crypto, SSRF, path traversal,
  insecure CORS/config, etc.)
- 🧹 Code smell detection (long functions, deep nesting, duplicate code,
  magic numbers, too many parameters, dead/commented-out code, poor naming)
- 🚦 Severity classification: `critical / high / medium / low / info`
- 💬 Plain-English explanation of *why* each issue matters
- 🛠️ Suggested fix / patched snippet for every issue
- 📊 Complexity & maintainability metrics + an overall **risk score**
- 🌐 Multi-language: Python, JavaScript/TypeScript, Java, Go, C/C++, generic fallback
- 🧠 Hybrid analysis: static rules (fast, free, deterministic) + LLM (deep, contextual)
- ⚡ In-memory result caching (identical code isn't re-analyzed/re-billed)
- 🖥️ Web UI — paste or drag-and-drop a file, filter results by severity
- 🧰 CLI tool for local use or CI/CD gating (`--fail-on high` exits non-zero)
- 📁 Batch/repo mode — recursively reviews a whole directory
- 📄 Export reports as Markdown or JSON
- 🤖 Ready-made GitHub Actions workflow that reviews PR diffs automatically
- 🐳 Dockerized, with `docker-compose` for one-command startup

---

## Project layout

```
ai-code-review-agent/
├── backend/
│   ├── main.py            # FastAPI app & routes
│   ├── analyzer.py        # Core hybrid analysis engine
│   ├── static_rules.py    # Regex/heuristic rule sets per language
│   ├── metrics.py         # Complexity / maintainability metrics
│   ├── llm_client.py      # Claude API wrapper
│   ├── models.py          # Pydantic schemas
│   ├── report.py          # Markdown/JSON report rendering
│   ├── cache.py           # Simple hash-based result cache
│   └── config.py          # Settings via environment variables
├── cli/
│   └── review_cli.py      # Command-line client (local files or via API)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── examples/
│   └── vulnerable_sample.py
├── tests/
│   └── test_analyzer.py
├── .github/workflows/code-review.yml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## Setup

```bash
git clone <your-repo-url>
cd ai-code-review-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
```

### Run the server

```bash
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** for the web UI.

### Run with Docker

```bash
docker compose up --build
```

---

## API

### `POST /api/review`

```json
{
  "code": "def add(a, b):\n    return a+b",
  "filename": "math_utils.py"
}
```

Returns a `ReviewReport` (see `backend/models.py`) containing `issues[]`,
`metrics`, `summary`, and `risk_score`.

### `GET /api/health`

Liveness check.

---

## CLI usage

```bash
# Review a single file locally (spins up the analysis in-process, no server needed)
python cli/review_cli.py review path/to/file.py

# Review an entire repo, skipping vendored folders
python cli/review_cli.py review . --recursive

# Use as a CI gate: exit code 1 if any HIGH or CRITICAL issue is found
python cli/review_cli.py review . --recursive --fail-on high

# Point the CLI at a running server instead of analyzing in-process
python cli/review_cli.py review . --recursive --server http://localhost:8000

# Export a Markdown report
python cli/review_cli.py review . --recursive --format markdown --output report.md
```

---

## CI/CD integration

`.github/workflows/code-review.yml` runs the CLI against changed files on
every pull request and fails the check if a `critical`/`high` issue is found,
posting a summary as a workflow annotation. Set the `ANTHROPIC_API_KEY`
repository secret to enable it.

---

## How severity is decided

| Severity | Meaning |
|---|---|
| **critical** | Actively exploitable security hole or a bug that will corrupt data / crash in production |
| **high** | Serious security or correctness issue, exploitable/triggerable in common paths |
| **medium** | Real issue, but needs specific conditions or has partial mitigations |
| **low** | Minor bug/smell, unlikely to cause real-world harm |
| **info** | Style/maintainability suggestion, no functional risk |

---

## Notes & limitations

- The LLM pass requires an `ANTHROPIC_API_KEY`. Without one, the tool still
  runs in **static-only mode** (rule-based findings only) — see `config.py`.
- This is a developer-productivity aid, not a substitute for a dedicated SAST
  tool, dependency scanner, or manual security review on critical systems.
- Static rules aim for high-confidence, low-noise pattern matches; the LLM
  pass is what finds novel/contextual issues, so review quality scales with
  which model you configure in `.env`.
