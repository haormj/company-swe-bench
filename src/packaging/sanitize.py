"""De-identification for task artifacts.

``instruction.md`` (and other agent-visible text) must not leak internal links
or secret-looking content. Public URLs are preserved.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence

DEFAULT_SENSITIVE_PATTERNS = [
    "-----BEGIN",
    "PRIVATE KEY",
    "AKIA",
    "aws_secret_access_key",
]

_INTERNAL_HOST_HINTS = (
    "internal",
    "intranet",
    ".corp",
    "gitlab.internal",
    "localhost",
    "127.0.0.1",
    ".local",
    "wiki.",
)

_URL_RE = re.compile(r"https?://[^\s)\]\"'>]+", re.IGNORECASE)

LINK_PLACEHOLDER = "[redacted-internal-link]"
SECRET_PLACEHOLDER = "[redacted-secret]"


def is_internal_url(url: str) -> bool:
    lowered = url.lower()
    return any(hint in lowered for hint in _INTERNAL_HOST_HINTS)


def sanitize_text(
    text: str,
    sensitive_patterns: Sequence[str] = DEFAULT_SENSITIVE_PATTERNS,
) -> str:
    """Redact internal links and sensitive substrings from *text*."""
    def _replace_url(match: "re.Match[str]") -> str:
        url = match.group(0)
        return LINK_PLACEHOLDER if is_internal_url(url) else url

    cleaned = _URL_RE.sub(_replace_url, text)
    for pattern in sensitive_patterns:
        cleaned = cleaned.replace(pattern, SECRET_PLACEHOLDER)
    return cleaned


def find_sensitive(
    text: str, patterns: Sequence[str] = DEFAULT_SENSITIVE_PATTERNS
) -> List[str]:
    return [p for p in patterns if p in text]


def find_internal_links(text: str) -> List[str]:
    return [m.group(0) for m in _URL_RE.finditer(text) if is_internal_url(m.group(0))]


def is_clean(
    text: str, patterns: Sequence[str] = DEFAULT_SENSITIVE_PATTERNS
) -> bool:
    return not find_sensitive(text, patterns) and not find_internal_links(text)
