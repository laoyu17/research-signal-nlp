"""Text preprocessing utilities."""

from __future__ import annotations

import re

PUNCT_RE = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9 ]+")
SPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    cleaned = PUNCT_RE.sub(" ", text)
    return SPACE_RE.sub(" ", cleaned).strip().lower()
