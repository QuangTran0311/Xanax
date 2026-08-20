"""Sanitize provider/CLI failures before they cross an API boundary."""
from __future__ import annotations

import re


def safe_provider_error(message: object, entry: dict | None = None) -> str:
    """Return a short diagnostic without credentials, tokens, or config paths."""
    text = " ".join(str(message or "").split())
    entry = entry or {}

    config_dir = str(entry.get("cli_config_dir") or "").strip()
    if config_dir:
        variants = {
            config_dir,
            config_dir.replace("\\", "/"),
            config_dir.replace("/", "\\"),
            config_dir.replace("\\", "\\\\"),
        }
        for variant in sorted(variants, key=len, reverse=True):
            if variant:
                text = re.sub(
                    re.escape(variant), "<credential directory>", text, flags=re.IGNORECASE,
                )

    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1<redacted>", text)
    text = re.sub(
        r"(?i)\b((?:[a-z0-9]+_)*(?:api[_-]?key|auth[_-]?token|refresh[_-]?token|"
        r"access[_-]?token|token|secret|password))\b\s*[:=]\s*[^\s,;]+",
        r"\1=<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)(?:[a-z]:\\users\\[^\\\s]+\\|/home/[^/\s]+/)?"
        r"\.(?:claude|codex)(?:[/\\][^\s,;:]*)*",
        "<credential path>",
        text,
    )
    text = re.sub(
        r"(?i)\b(?:CODEX_HOME|CLAUDE_CONFIG_DIR)\b(?:\s*[:=]\s*[^\s,;]+)?",
        "<credential environment>",
        text,
    )
    return text[:180] or "CLI failed without a diagnostic"
