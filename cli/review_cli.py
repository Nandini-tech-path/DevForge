#!/usr/bin/env python3
"""
Command-line client for the AI Code Review agent.

Usage:
    python cli/review_cli.py review <path> [options]

Options:
    --recursive              Walk directories recursively
    --server <url>           Use a running server's /api/review endpoint instead
                              of analyzing in-process
    --format json|markdown   Output format (default: markdown, printed to stdout)
    --output <file>          Write report(s) to a file instead of stdout
    --fail-on <severity>     Exit non-zero if any issue >= this severity is found
                              (critical|high|medium|low). Useful for CI gating.
    --ext .py,.js            Restrict to specific extensions (comma separated)
"""
import argparse
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import SEVERITY_WEIGHT, Severity  # noqa: E402
from backend.report import to_markdown  # noqa: E402

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".idea", ".vscode"}
DEFAULT_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".c", ".cpp", ".rb", ".php", ".cs", ".rs"}


def collect_files(path: str, recursive: bool, exts: set) -> list:
    if os.path.isfile(path):
        return [path]

    files = []
    if recursive:
        for root, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in filenames:
                if os.path.splitext(fname)[1] in exts:
                    files.append(os.path.join(root, fname))
    else:
        for fname in os.listdir(path):
            full = os.path.join(path, fname)
            if os.path.isfile(full) and os.path.splitext(fname)[1] in exts:
                files.append(full)
    return sorted(files)


def review_via_server(server: str, code: str, filename: str) -> dict:
    resp = httpx.post(f"{server}/api/review", json={"code": code, "filename": filename}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def review_in_process(code: str, filename: str):
    from backend.analyzer import review_code
    return review_code(code, filename)


def main():
    parser = argparse.ArgumentParser(description="AI Code Review CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_review = sub.add_parser("review", help="Review a file or directory")
    p_review.add_argument("path", help="File or directory to review")
    p_review.add_argument("--recursive", action="store_true")
    p_review.add_argument("--server", default=None, help="Base URL of a running server, e.g. http://localhost:8000")
    p_review.add_argument("--format", choices=["json", "markdown"], default="markdown")
    p_review.add_argument("--output", default=None)
    p_review.add_argument("--fail-on", choices=["critical", "high", "medium", "low"], default=None)
    p_review.add_argument("--ext", default=None, help="Comma-separated list of extensions to include")

    args = parser.parse_args()

    exts = set(args.ext.split(",")) if args.ext else DEFAULT_EXTS
    files = collect_files(args.path, args.recursive, exts)

    if not files:
        print("No matching files found.", file=sys.stderr)
        sys.exit(1)

    reports = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                code = fh.read()
        except Exception as e:
            print(f"Skipping {f}: {e}", file=sys.stderr)
            continue

        if not code.strip():
            continue

        rel = os.path.relpath(f, start=os.getcwd())
        print(f"Reviewing {rel} ...", file=sys.stderr)

        try:
            if args.server:
                data = review_via_server(args.server, code, rel)
                from backend.models import ReviewReport
                report = ReviewReport(**data)
            else:
                report = review_in_process(code, rel)
        except Exception as e:
            print(f"  -> failed: {e}", file=sys.stderr)
            continue

        reports.append(report)

    output_chunks = []
    worst_weight = -1
    for report in reports:
        if args.format == "markdown":
            output_chunks.append(to_markdown(report))
        else:
            output_chunks.append(report.model_dump_json(indent=2))
        for issue in report.issues:
            worst_weight = max(worst_weight, SEVERITY_WEIGHT[issue.severity])

    separator = "\n\n---\n\n" if args.format == "markdown" else ",\n"
    final_output = separator.join(output_chunks) if args.format == "markdown" else f"[{separator.join(output_chunks)}]"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(final_output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(final_output)

    total_issues = sum(len(r.issues) for r in reports)
    print(f"\n{total_issues} issue(s) found across {len(reports)} file(s).", file=sys.stderr)

    if args.fail_on:
        threshold = SEVERITY_WEIGHT[Severity(args.fail_on)]
        if worst_weight >= threshold:
            print(f"Failing: issue at or above '{args.fail_on}' severity found.", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
