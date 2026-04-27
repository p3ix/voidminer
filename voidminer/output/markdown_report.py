from __future__ import annotations

from voidminer.models import Confidence, Report


def _manual_validation_tips(parameter: str) -> list[str]:
    return [
        f"Try {parameter}=true",
        f"Try {parameter}=1",
        f"Try {parameter}=verbose",
        "Check whether sensitive data appears in the response",
    ]


def render_markdown_report(report: Report) -> str:
    s = report.summary
    lines = [
        "# VoidMiner Report",
        "",
        "## Summary",
        f"- Target URLs tested: {s.target_urls_tested}",
        f"- Parameters tested: {s.parameters_tested}",
        f"- Payloads executed: {s.payloads_executed}",
        f"- Signals detected: {s.signals_detected}",
        f"- Signal ratio: {s.signal_ratio:.3f}",
        f"- Multi-payload confirmed findings: {s.findings_confirmed_multi_payload}",
        f"- Request errors: {s.request_errors}",
        f"- Retry attempts: {s.retry_attempts}",
        f"- Elapsed seconds: {s.elapsed_seconds:.2f}",
        f"- Findings per minute: {s.findings_per_minute:.2f}",
        f"- Parameters per minute: {s.parameters_per_minute:.2f}",
        f"- Time to first finding (s): {s.time_to_first_finding_s:.2f}",
        f"- Phase1 candidates: {s.phase1_candidates}",
        f"- Confirmed findings: {s.confirmed_findings}",
        f"- Candidate->confirmed ratio: {s.candidates_to_confirmed_ratio:.3f}",
        f"- Findings: {s.findings}",
        f"- High: {s.high}",
        f"- Medium: {s.medium}",
        f"- Low: {s.low}",
        "",
        "## Endpoint Metrics",
        "",
    ]

    for endpoint_summary in report.endpoints:
        lines.extend(
            [
                f"### `{endpoint_summary.endpoint}`",
                f"- Parameters tested: {endpoint_summary.parameters_tested}",
                f"- Payloads executed: {endpoint_summary.payloads_executed}",
                f"- Signals detected: {endpoint_summary.signals_detected}",
                f"- Request errors: {endpoint_summary.request_errors}",
                f"- Retry attempts: {endpoint_summary.retry_attempts}",
                f"- Findings: {endpoint_summary.findings}",
                f"- High: {endpoint_summary.high}",
                f"- Medium: {endpoint_summary.medium}",
                f"- Low: {endpoint_summary.low}",
                "",
            ]
        )

    lines.extend(
        [
            "## Quick Triage",
            "",
        ]
    )
    top_findings = sorted(report.findings, key=lambda f: f.score, reverse=True)[:10]
    if not top_findings:
        lines.append("- No findings")
    else:
        for finding in top_findings:
            lines.append(f"- [{finding.confidence.value}] {finding.endpoint} :: {finding.parameter} (score={finding.score})")
    lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )

    for finding in report.findings:
        lines.extend(
            [
                f"### [{finding.confidence.value}] Hidden parameter: {finding.parameter}",
                "",
                "Endpoint:",
                f"`{finding.endpoint}`",
                "",
                "Location:",
                f"`{finding.location.value}`",
                "",
                "Payload:",
                f"`{finding.payload}`",
                "",
                "Payload execution:",
                f"- Payloads tested: {', '.join(finding.payloads_tested)}",
                f"- Payloads with signal: {', '.join(finding.payloads_with_signal) if finding.payloads_with_signal else '-'}",
                f"- Payloads executed: {finding.payloads_executed}",
                f"- Signal hits: {finding.signal_hits}",
                "",
                "Evidence:",
                f"- Status changed: {finding.evidence.status_changed}",
                f"- Content length changed: {finding.evidence.length_delta}",
                f"- Reflected value: {'yes' if finding.evidence.reflected else 'no'}",
                f"- New JSON keys: {', '.join(finding.evidence.new_json_keys) if finding.evidence.new_json_keys else '-'}",
                "",
                "Risk:",
                "This parameter may expose internal functionality or insecure logic paths.",
                "",
                "Suggested manual validation:",
            ]
        )
        lines.extend(f"- {tip}" for tip in _manual_validation_tips(finding.parameter))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_markdown_report(path: str, report: Report) -> None:
    content = render_markdown_report(report)
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)
