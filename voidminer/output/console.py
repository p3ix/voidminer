from __future__ import annotations

from rich.console import Console
from rich.table import Table

from voidminer.models import EndpointSummary, Finding, Report


console = Console()


def info(message: str, silent: bool = False) -> None:
    if not silent:
        console.print(f"[cyan][*][/cyan] {message}")


def success(message: str, silent: bool = False) -> None:
    if not silent:
        console.print(f"[green][+][/green] {message}")


def warn(message: str, silent: bool = False) -> None:
    if not silent:
        console.print(f"[yellow][!][/yellow] {message}")


def print_endpoint_metrics(endpoints: list[EndpointSummary], silent: bool = False) -> None:
    if silent or not endpoints:
        return
    table = Table(title="Endpoint Metrics")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Params", justify="right")
    table.add_column("Payloads", justify="right")
    table.add_column("Signals", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Retries", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("High", justify="right")
    table.add_column("Med", justify="right")
    table.add_column("Low", justify="right")

    for endpoint in endpoints:
        table.add_row(
            endpoint.endpoint,
            str(endpoint.parameters_tested),
            str(endpoint.payloads_executed),
            str(endpoint.signals_detected),
            str(endpoint.request_errors),
            str(endpoint.retry_attempts),
            str(endpoint.findings),
            str(endpoint.high),
            str(endpoint.medium),
            str(endpoint.low),
        )
    console.print(table)


def progress(current: int, total: int, silent: bool = False) -> None:
    if silent:
        return
    if total <= 0:
        return
    if current == total:
        console.print(f"[cyan][*][/cyan] Progress: {current}/{total} (done)")
    else:
        console.print(f"[cyan][*][/cyan] Progress: {current}/{total}")


def print_quick_triage(report: Report, silent: bool = False, limit: int = 10) -> None:
    if silent or not report.findings:
        return
    top_findings = sorted(report.findings, key=lambda f: f.score, reverse=True)[:limit]
    triage_table = Table(title="Quick Triage - Top Findings")
    triage_table.add_column("Endpoint", style="cyan")
    triage_table.add_column("Parameter")
    triage_table.add_column("Confidence")
    triage_table.add_column("Score", justify="right")
    for finding in top_findings:
        triage_table.add_row(finding.endpoint, finding.parameter, finding.confidence.value, str(finding.score))
    console.print(triage_table)
