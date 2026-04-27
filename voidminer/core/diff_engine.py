from __future__ import annotations

import json

from voidminer.core.normalizer import normalize_text
from voidminer.core.requester import HTTPResult
from voidminer.models import BaselineFingerprint, DiffResult, Evidence, ResponseSnapshot
from voidminer.utils.hashing import sha256_text


INTERESTING_HEADERS = {"x-debug", "x-runtime", "x-powered-by", "x-env", "server-timing"}


def _json_keys(text: str) -> set[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return set()
    if isinstance(payload, dict):
        return set(str(k) for k in payload.keys())
    return set()


def _is_technical_error(text: str) -> bool:
    lower = text.lower()
    markers = ["stack trace", "exception", "traceback", "sql syntax", "fatal error"]
    return any(marker in lower for marker in markers)


def compare_with_baseline(
    baseline: BaselineFingerprint,
    response: HTTPResult,
    canary: str,
    length_threshold: int = 20,
    timing_threshold_ms: float = 500.0,
) -> DiffResult:
    normalized = normalize_text(response.text)
    body_hash = sha256_text(normalized)
    status_changed = response.status_code != baseline.status_code
    length_delta = response.content_length - baseline.content_length
    body_hash_changed = body_hash != baseline.body_hash
    new_headers = sorted(set(response.headers.keys()) - set(baseline.headers))
    removed_headers = sorted(set(baseline.headers) - set(response.headers.keys()))
    reflected = canary.lower() in response.text.lower()
    current_json_keys = _json_keys(response.text)
    base_json_keys = set(baseline.json_keys)
    new_json_keys = sorted(current_json_keys - base_json_keys)
    removed_json_keys = sorted(base_json_keys - current_json_keys)
    timing_delta = response.response_time_ms - baseline.response_time_ms
    auth_bypass_signal = baseline.status_code in {401, 403} and response.status_code in {200, 302}
    technical_error = _is_technical_error(response.text)

    evidence = Evidence(
        status_changed=status_changed,
        length_delta=length_delta if abs(length_delta) >= length_threshold else 0,
        reflected=reflected,
        new_headers=[h for h in new_headers if h in INTERESTING_HEADERS],
        removed_headers=removed_headers,
        new_json_keys=new_json_keys,
        removed_json_keys=removed_json_keys,
        timing_delta_ms=timing_delta if timing_delta >= timing_threshold_ms else 0.0,
        body_hash_changed=body_hash_changed,
        technical_error=technical_error,
        auth_bypass_signal=auth_bypass_signal,
    )
    return DiffResult(
        evidence=evidence,
        response=ResponseSnapshot(
            status_code=response.status_code,
            content_length=response.content_length,
            response_time_ms=response.response_time_ms,
            sample=response.text[:400],
        ),
        status_code_before=baseline.status_code,
        status_code_after=response.status_code,
        content_length_before=baseline.content_length,
        content_length_after=response.content_length,
    )
