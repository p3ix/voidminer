from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from voidminer.core.baseline import build_baseline
from voidminer.core.diff_engine import compare_with_baseline
from voidminer.core.injector import inject_query_param
from voidminer.core.requester import Requester
from voidminer.core.scorer import score_evidence, score_to_confidence
from voidminer.models import BaselineFingerprint, Finding, Location, RequestSnapshot
from voidminer.utils.randoms import build_canary


def run_query_miner(
    requester: Requester,
    urls: list[str],
    wordlist: list[str],
    method: str,
    headers: dict[str, str],
    min_score: int,
    threads: int = 10,
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    tested_params = len(urls) * len(wordlist)
    baselines: dict[str, BaselineFingerprint] = {}
    for url in urls:
        baselines[url], _ = build_baseline(requester, url, method=method)

    def _scan_param(target_url: str, parameter: str) -> Finding | None:
        baseline = baselines[target_url]
        canary = build_canary()
        injected_url = inject_query_param(target_url, parameter, canary)
        response = requester.request(method, injected_url, headers=headers)
        diff = compare_with_baseline(baseline=baseline, response=response, canary=canary)
        score = score_evidence(diff.evidence)
        confidence = score_to_confidence(score)
        if confidence is None or score < min_score:
            return None
        return Finding(
            endpoint=target_url,
            method=method.upper(),
            parameter=parameter,
            location=Location.QUERY,
            payload=f"?{parameter}={canary}",
            confidence=confidence,
            score=score,
            evidence=diff.evidence,
            request=RequestSnapshot(url=injected_url, headers=headers, body=None),
            response=diff.response,
        )

    max_workers = max(1, threads)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_scan_param, url, parameter) for url in urls for parameter in wordlist]
        for future in as_completed(futures):
            finding = future.result()
            if finding:
                findings.append(finding)

    findings.sort(key=lambda x: (x.endpoint, -x.score, x.parameter))
    return findings, tested_params
