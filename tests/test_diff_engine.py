from voidminer.core.diff_engine import compare_with_baseline
from voidminer.core.requester import HTTPResult
from voidminer.models import BaselineFingerprint


def test_diff_detects_reflection_and_json_key() -> None:
    baseline = BaselineFingerprint(
        status_code=200,
        content_length=20,
        body_hash="abc",
        header_hash="def",
        response_time_ms=100.0,
        headers=["content-type"],
        json_keys=["ok"],
    )
    response = HTTPResult(
        url="https://example.com",
        method="GET",
        status_code=200,
        headers={"content-type": "application/json", "x-debug": "1"},
        text='{"ok":true,"debug":"voidminer_x"}',
        content_length=40,
        response_time_ms=800.0,
    )
    diff = compare_with_baseline(baseline, response, "voidminer_x")
    assert diff.evidence.reflected is True
    assert "debug" in diff.evidence.new_json_keys
    assert "x-debug" in diff.evidence.new_headers
