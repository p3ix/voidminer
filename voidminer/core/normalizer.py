from __future__ import annotations

import re


NOISE_PATTERNS = [
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"), "<uuid>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b"), "<iso_ts>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "<date>"),
    (re.compile(r"\b(?:csrf|nonce|request_id|trace_id)[\"'=:\s]+[A-Za-z0-9_\-]{6,}\b", re.IGNORECASE), "<token>"),
    (re.compile(r"\b\d{10,}\b"), "<large_num>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}\b"), "<time>"),
]


def normalize_text(value: str) -> str:
    normalized = value
    for pattern, replacement in NOISE_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
