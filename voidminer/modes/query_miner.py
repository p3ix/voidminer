from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import time
from typing import Callable

from voidminer.core.baseline import build_baseline
from voidminer.core.diff_engine import compare_with_baseline
from voidminer.core.injector import inject_query_param
from voidminer.core.requester import HTTPRequestError, Requester
from voidminer.core.scorer import score_evidence, score_multi_payload, score_to_confidence
from voidminer.models import BaselineFingerprint, Finding, Location, RequestSnapshot
from voidminer.utils.randoms import build_canary, build_payload_candidates


def run_query_miner(
    requester: Requester,
    urls: list[str],
    wordlist: list[str],
    method: str,
    headers: dict[str, str],
    min_score: int,
    threads: int = 10,
    payload_profile: str = "balanced",
    max_payloads_per_param: int = 6,
    early_stop_on_strong_signal: bool = True,
    two_phase_scan: bool = False,
    phase1_payload_profile: str = "fast",
    phase1_max_payloads_per_param: int = 2,
    phase1_min_score: int = 2,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[list[Finding], int, int, dict[str, dict[str, int]], dict[str, int]]:
    findings: list[Finding] = []
    tested_params = len(urls) * len(wordlist)
    errors_count = 0
    endpoint_errors: dict[str, int] = defaultdict(int)
    endpoint_tested: dict[str, int] = {url: len(wordlist) for url in urls}
    endpoint_payloads_executed: dict[str, int] = defaultdict(int)
    endpoint_signals_detected: dict[str, int] = defaultdict(int)
    payloads_executed = 0
    signals_detected = 0
    phase1_candidates = 0
    completed_tasks = 0
    total_tasks = tested_params
    start_ts = time.perf_counter()
    first_finding_elapsed_s = 0.0
    baselines: dict[str, BaselineFingerprint] = {}
    for url in urls:
        try:
            baselines[url], _ = build_baseline(requester, url, method=method)
        except HTTPRequestError:
            errors_count += 1
            endpoint_errors[url] += 1

    def _evaluate_payloads(
        *,
        target_url: str,
        parameter: str,
        baseline: BaselineFingerprint,
        method: str,
        headers: dict[str, str],
        payload_candidates: list[str],
        canary: str,
        early_stop: bool,
        strong_signal_threshold: int = 8,
    ) -> tuple[int, list, dict[str, object], list[str], str, object, int, int]:
        evidences = []
        evidence_by_payload = {}
        payloads_with_signal: list[str] = []
        last_injected_url = target_url
        last_diff = None
        local_payloads = 0
        local_signals = 0
        for payload in payload_candidates:
            local_payloads += 1
            last_injected_url = inject_query_param(target_url, parameter, payload)
            response = requester.request(method, last_injected_url, headers=headers)
            diff = compare_with_baseline(baseline=baseline, response=response, canary=canary)
            last_diff = diff
            evidences.append(diff.evidence)
            evidence_by_payload[payload] = diff.evidence
            payload_score = score_evidence(diff.evidence)
            if payload_score > 0:
                local_signals += 1
                payloads_with_signal.append(payload)
            if early_stop and payload_score >= strong_signal_threshold:
                break
        aggregate_score = score_multi_payload(evidences)
        return aggregate_score, evidences, evidence_by_payload, payloads_with_signal, last_injected_url, last_diff, local_payloads, local_signals

    def _scan_param(target_url: str, parameter: str) -> tuple[Finding | None, int, int, bool]:
        if target_url not in baselines:
            return None, 0, 0, False
        baseline = baselines[target_url]
        canary = build_canary()
        phase1_payloads = build_payload_candidates(phase1_payload_profile, canary)[: max(1, phase1_max_payloads_per_param)]
        phase1_score, phase1_evidences, phase1_by_payload, phase1_hits, phase1_last_url, phase1_last_diff, phase1_count, phase1_signals = _evaluate_payloads(
            target_url=target_url,
            parameter=parameter,
            baseline=baseline,
            method=method,
            headers=headers,
            payload_candidates=phase1_payloads,
            canary=canary,
            early_stop=True,
            strong_signal_threshold=8,
        )
        if phase1_last_diff is None:
            return None, phase1_count, phase1_signals, False

        candidate = phase1_score >= phase1_min_score
        if not two_phase_scan:
            candidate = True

        if not candidate:
            return None, phase1_count, phase1_signals, False

        if two_phase_scan:
            payload_candidates = build_payload_candidates(payload_profile, canary)[: max(1, max_payloads_per_param)]
            score, evidences, evidence_by_payload, payloads_with_signal, last_injected_url, last_diff, deep_count, deep_signals = _evaluate_payloads(
                target_url=target_url,
                parameter=parameter,
                baseline=baseline,
                method=method,
                headers=headers,
                payload_candidates=payload_candidates,
                canary=canary,
                early_stop=early_stop_on_strong_signal,
                strong_signal_threshold=8,
            )
            local_payloads = phase1_count + deep_count
            local_signals = phase1_signals + deep_signals
        else:
            payload_candidates = phase1_payloads
            score = phase1_score
            evidences = phase1_evidences
            evidence_by_payload = phase1_by_payload
            payloads_with_signal = phase1_hits
            last_injected_url = phase1_last_url
            last_diff = phase1_last_diff
            local_payloads = phase1_count
            local_signals = phase1_signals

        confidence = score_to_confidence(score)
        if confidence is None or score < min_score:
            return None, local_payloads, local_signals, candidate
        assert last_diff is not None
        return Finding(
            endpoint=target_url,
            method=method.upper(),
            parameter=parameter,
            location=Location.QUERY,
            payload=f"?{parameter}={canary}",
            payloads_tested=payload_candidates,
            payloads_with_signal=payloads_with_signal,
            payloads_executed=local_payloads,
            signal_hits=local_signals,
            confidence=confidence,
            score=score,
            evidence=evidences[-1] if evidences else last_diff.evidence,
            evidence_by_payload=evidence_by_payload,
            request=RequestSnapshot(url=last_injected_url, headers=headers, body=None),
            response=last_diff.response,
        ), local_payloads, local_signals, candidate

    max_workers = max(1, threads)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks_map = {
            executor.submit(_scan_param, url, parameter): (url, parameter) for url in urls for parameter in wordlist
        }
        futures = list(tasks_map.keys())
        for future in as_completed(futures):
            try:
                finding, local_payloads, local_signals, candidate = future.result()
            except HTTPRequestError:
                errors_count += 1
                _url, _parameter = tasks_map[future]
                endpoint_errors[_url] += 1
                continue
            _url, _parameter = tasks_map[future]
            completed_tasks += 1
            payloads_executed += local_payloads
            signals_detected += local_signals
            endpoint_payloads_executed[_url] += local_payloads
            endpoint_signals_detected[_url] += local_signals
            if candidate:
                phase1_candidates += 1
            if finding:
                if first_finding_elapsed_s == 0.0:
                    first_finding_elapsed_s = time.perf_counter() - start_ts
                findings.append(finding)
            if progress_callback and (completed_tasks % 100 == 0 or completed_tasks == total_tasks):
                progress_callback(completed_tasks, total_tasks)

    findings.sort(key=lambda x: (x.endpoint, -x.score, x.parameter))
    endpoint_findings: dict[str, int] = defaultdict(int)
    for finding in findings:
        endpoint_findings[finding.endpoint] += 1

    endpoint_stats = {
        url: {
            "parameters_tested": endpoint_tested.get(url, 0),
            "payloads_executed": endpoint_payloads_executed.get(url, 0),
            "signals_detected": endpoint_signals_detected.get(url, 0),
            "request_errors": endpoint_errors.get(url, 0),
            "findings": endpoint_findings.get(url, 0),
        }
        for url in urls
    }
    scan_metrics = {
        "payloads_executed": payloads_executed,
        "signals_detected": signals_detected,
        "phase1_candidates": phase1_candidates,
        "elapsed_seconds": time.perf_counter() - start_ts,
        "time_to_first_finding_s": first_finding_elapsed_s,
    }
    return findings, tested_params, errors_count, endpoint_stats, scan_metrics
