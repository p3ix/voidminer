from __future__ import annotations

from voidminer.models import Confidence, Evidence


def score_evidence(evidence: Evidence) -> int:
    score = 0
    if evidence.status_changed:
        score += 1
    if evidence.length_delta != 0:
        score += 1
    if evidence.body_hash_changed:
        score += 2
    if evidence.reflected:
        score += 3
    if evidence.new_headers:
        score += 3
    if evidence.new_json_keys:
        score += 3
    if evidence.technical_error:
        score += 4
    if evidence.timing_delta_ms > 0:
        score += 5
    if evidence.auth_bypass_signal:
        score += 5
    return score


def score_to_confidence(score: int) -> Confidence | None:
    if score <= 2:
        return None
    if score <= 5:
        return Confidence.LOW
    if score <= 9:
        return Confidence.MEDIUM
    return Confidence.HIGH
