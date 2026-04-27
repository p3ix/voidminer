from voidminer.core.scorer import score_evidence, score_multi_payload, score_to_confidence
from voidminer.models import Confidence, Evidence


def test_score_and_confidence_medium() -> None:
    evidence = Evidence(
        status_changed=True,
        body_hash_changed=True,
        reflected=True,
    )
    score = score_evidence(evidence)
    assert score == 6
    assert score_to_confidence(score) == Confidence.MEDIUM


def test_score_below_threshold_is_ignored() -> None:
    score = score_evidence(Evidence(status_changed=True))
    assert score == 1
    assert score_to_confidence(score) is None


def test_score_multi_payload_rewards_consistency() -> None:
    e1 = Evidence(reflected=True, new_json_keys=["debug"])
    e2 = Evidence(reflected=True)
    score = score_multi_payload([e1, e2])
    assert score >= score_evidence(e1)
