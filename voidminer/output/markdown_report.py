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
        f"- Findings: {s.findings}",
        f"- High: {s.high}",
        f"- Medium: {s.medium}",
        f"- Low: {s.low}",
        "",
        "## Findings",
        "",
    ]

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
