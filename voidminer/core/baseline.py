from __future__ import annotations

import json
from collections import Counter
from statistics import median

from bs4 import BeautifulSoup

from voidminer.core.normalizer import normalize_text
from voidminer.core.requester import HTTPResult, Requester
from voidminer.models import BaselineFingerprint
from voidminer.utils.hashing import sha256_text


def _extract_json_keys(text: str) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        return sorted(str(k) for k in payload.keys())
    return []


def _extract_html_features(text: str) -> tuple[str | None, int, list[str]]:
    soup = BeautifulSoup(text, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else None
    forms = soup.find_all("form")
    input_names = sorted({el.get("name", "") for el in soup.find_all("input") if el.get("name")})
    return title, len(forms), input_names


def build_baseline(requester: Requester, url: str, method: str = "GET") -> tuple[BaselineFingerprint, list[HTTPResult]]:
    samples = [requester.request(method, url) for _ in range(3)]
    normalized_bodies = [normalize_text(s.text) for s in samples]
    body_hashes = [sha256_text(body) for body in normalized_bodies]
    header_hashes = [sha256_text("|".join(f"{k}:{v}" for k, v in sorted(s.headers.items()))) for s in samples]
    status_counter = Counter(s.status_code for s in samples)
    status_code = status_counter.most_common(1)[0][0]
    content_length = round(median([s.content_length for s in samples]))
    response_time_ms = float(median([s.response_time_ms for s in samples]))
    dominant_body_hash = Counter(body_hashes).most_common(1)[0][0]
    dominant_header_hash = Counter(header_hashes).most_common(1)[0][0]
    representative_idx = body_hashes.index(dominant_body_hash)
    representative = samples[representative_idx]
    json_keys = _extract_json_keys(representative.text)
    html_title, html_forms, html_input_names = _extract_html_features(representative.text)

    fingerprint = BaselineFingerprint(
        status_code=status_code,
        content_length=content_length,
        body_hash=dominant_body_hash,
        header_hash=dominant_header_hash,
        response_time_ms=response_time_ms,
        headers=sorted(representative.headers.keys()),
        json_keys=json_keys,
        html_title=html_title,
        html_forms=html_forms,
        html_input_names=html_input_names,
    )
    return fingerprint, samples
