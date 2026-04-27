from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from voidminer.models import Confidence, Report, ScanSummary
from voidminer.modes.query_miner import run_query_miner
from voidminer.output.json_report import write_json_report
from voidminer.output.markdown_report import write_markdown_report
from voidminer.core.requester import Requester


def _mock_handler(request: httpx.Request) -> httpx.Response:
    parsed = urlparse(str(request.url))
    query = parse_qs(parsed.query)
    debug_value = query.get("debug", [None])[0]
    if debug_value:
        body = f'{{"ok":true,"debug":"{debug_value}"}}'
        headers = {"content-type": "application/json", "x-debug": "enabled"}
        return httpx.Response(status_code=200, headers=headers, text=body, request=request)
    return httpx.Response(
        status_code=200,
        headers={"content-type": "application/json"},
        text='{"ok":true,"trace_id":"abc123","epoch":1711111111111}',
        request=request,
    )


def test_query_miner_pipeline_with_mock_transport() -> None:
    requester = Requester(timeout=2.0, rate=1000.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(_mock_handler), follow_redirects=True)
    try:
        findings, tested_params, errors_count, endpoint_stats, scan_metrics = run_query_miner(
            requester=requester,
            urls=["https://target.local/api/user"],
            wordlist=["debug"],
            method="GET",
            headers={},
            min_score=3,
            threads=2,
            payload_profile="fast",
            max_payloads_per_param=3,
            early_stop_on_strong_signal=True,
            two_phase_scan=True,
            phase1_payload_profile="fast",
            phase1_max_payloads_per_param=2,
            phase1_min_score=1,
        )
    finally:
        requester.close()

    assert tested_params == 1
    assert errors_count == 0
    assert scan_metrics["payloads_executed"] >= 1
    assert scan_metrics["phase1_candidates"] >= 1
    assert endpoint_stats["https://target.local/api/user"]["findings"] == 1
    assert len(findings) == 1
    finding = findings[0]
    assert finding.parameter == "debug"
    assert finding.confidence == Confidence.HIGH
    assert finding.evidence.reflected is True
    assert "x-debug" in finding.evidence.new_headers
    assert "debug" in finding.evidence.new_json_keys


def test_report_writers_with_real_finding(tmp_path: Path) -> None:
    requester = Requester(timeout=2.0, rate=1000.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(_mock_handler), follow_redirects=True)
    try:
        findings, tested_params, errors_count, endpoint_stats, scan_metrics = run_query_miner(
            requester=requester,
            urls=["https://target.local/api/user"],
            wordlist=["debug"],
            method="GET",
            headers={},
            min_score=3,
            threads=1,
            payload_profile="fast",
            max_payloads_per_param=3,
            early_stop_on_strong_signal=True,
        )
    finally:
        requester.close()

    report = Report(
        summary=ScanSummary(
            target_urls_tested=1,
            parameters_tested=tested_params,
            payloads_executed=scan_metrics["payloads_executed"],
            signals_detected=scan_metrics["signals_detected"],
            signal_ratio=0.0,
            findings_confirmed_multi_payload=0,
            request_errors=errors_count,
            retry_attempts=0,
            findings=len(findings),
            high=sum(1 for f in findings if f.confidence == Confidence.HIGH),
            medium=sum(1 for f in findings if f.confidence == Confidence.MEDIUM),
            low=sum(1 for f in findings if f.confidence == Confidence.LOW),
        ),
        endpoints=[],
        findings=findings,
    )
    json_path = tmp_path / "results.json"
    md_path = tmp_path / "results.md"
    write_json_report(str(json_path), report)
    write_markdown_report(str(md_path), report)

    json_content = json_path.read_text(encoding="utf-8")
    md_content = md_path.read_text(encoding="utf-8")
    assert '"parameter": "debug"' in json_content
    assert '"retry_attempts": 0' in json_content
    assert "# VoidMiner Report" in md_content
    assert "## Endpoint Metrics" in md_content
    assert "[HIGH] Hidden parameter: debug" in md_content
