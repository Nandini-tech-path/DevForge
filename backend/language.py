"""Language detection by file extension, with a content-based fallback."""
import os
import re

EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".rs": "rust",
}

CONTENT_HINTS = [
    (re.compile(r"^\s*def\s+\w+\s*\(.*\)\s*:"), "python"),
    (re.compile(r"^\s*import\s+\w+"), "python"),
    (re.compile(r"\bfunc\s+main\s*\(\s*\)"), "go"),
    (re.compile(r"\bpublic\s+class\s+\w+"), "java"),
    (re.compile(r"\b(const|let|var)\s+\w+\s*="), "javascript"),
]


def detect_language(filename: str, code: str) -> str:
    _, ext = os.path.splitext(filename or "")
    if ext.lower() in EXTENSION_MAP:
        return EXTENSION_MAP[ext.lower()]

    for pattern, lang in CONTENT_HINTS:
        if pattern.search(code):
            return lang

    return "generic"
