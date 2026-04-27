from __future__ import annotations

from pathlib import Path

import typer

from voidminer.config import ScanConfig
from voidminer.models import Confidence, EndpointSummary, Report, ScanSummary
from voidminer.modes.query_miner import run_query_miner
from voidminer.output.console import info, print_endpoint_metrics, print_quick_triage, progress, success, warn
from voidminer.output.json_report import write_json_report
from voidminer.output.markdown_report import write_markdown_report
from voidminer.core.requester import Requester
from voidminer.sources.wordlist_builder import list_wordlist_profiles, load_wordlists, prioritize_wordlist, resolve_wordlist_profile_paths

app = typer.Typer(add_completion=False, help="VoidMiner hidden parameter discovery engine")

OPS_PROFILE_DEFAULTS: dict[str, dict[str, object]] = {
    "recon_fast": {
        "threads": 20,
        "rate": 6.0,
        "retries": 0,
        "payload_profile": "fast",
        "max_payloads_per_param": 3,
        "two_phase_scan": True,
        "phase1_payload_profile": "fast",
        "phase1_max_payloads_per_param": 2,
        "phase1_min_score": 2,
    },
    "balanced": {
        "threads": 10,
        "rate": 4.0,
        "retries": 1,
        "payload_profile": "balanced",
        "max_payloads_per_param": 6,
        "two_phase_scan": False,
        "phase1_payload_profile": "fast",
        "phase1_max_payloads_per_param": 2,
        "phase1_min_score": 2,
    },
    "deep_confirm": {
        "threads": 6,
        "rate": 2.0,
        "retries": 2,
        "payload_profile": "deep",
        "max_payloads_per_param": 9,
        "two_phase_scan": True,
        "phase1_payload_profile": "balanced",
        "phase1_max_payloads_per_param": 4,
        "phase1_min_score": 2,
    },
}


def _read_lines(path: Path) -> list[str]:
    return load_wordlists([path])


def _parse_headers(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        if ":" not in item:
            raise typer.BadParameter(f"Invalid header format: {item}. Use 'Key: Value'.")
        key, value = item.split(":", 1)
        result[key.strip()] = value.strip()
    return result


@app.command()
def main(
    url: str | None = typer.Option(None, "-u", "--url", help="Single target URL"),
    list_path: Path | None = typer.Option(None, "-l", "--list", exists=True, file_okay=True, dir_okay=False, readable=True, help="File with target URLs"),
    wordlist_path: list[Path] = typer.Option([], "-w", "--wordlist", exists=True, file_okay=True, dir_okay=False, readable=True, help="Parameter wordlist file (repeatable)"),
    header: list[str] = typer.Option([], "-H", "--header", help="Custom header in 'Key: Value' format"),
    method: str = typer.Option("GET", "-X", "--method", help="HTTP method"),
    ops_profile: str = typer.Option("balanced", "--ops-profile", help="Ops profile: recon_fast, balanced, deep_confirm"),
    wordlist_profile: list[str] = typer.Option([], "--wordlist-profile", help="Wordlist profile (repeatable)"),
    threads: int = typer.Option(10, "--threads", min=1, help="Worker threads"),
    rate: float = typer.Option(5.0, "--rate", min=0.1, help="Requests per second"),
    timeout: float = typer.Option(10.0, "--timeout", min=0.1, help="HTTP timeout"),
    retries: int = typer.Option(0, "--retries", min=0, help="Retry attempts for transient request failures"),
    retry_backoff_ms: float = typer.Option(200.0, "--retry-backoff-ms", min=0.0, help="Base retry backoff in milliseconds"),
    retry_jitter_ms: float = typer.Option(100.0, "--retry-jitter-ms", min=0.0, help="Retry jitter in milliseconds"),
    payload_profile: str = typer.Option("balanced", "--payload-profile", help="Payload profile: fast, balanced, deep"),
    max_payloads_per_param: int = typer.Option(6, "--max-payloads-per-param", min=1, help="Maximum payload attempts per parameter"),
    early_stop_on_strong_signal: bool = typer.Option(True, "--early-stop-on-strong-signal/--no-early-stop-on-strong-signal", help="Stop payload testing early when strong signal is detected"),
    two_phase_scan: bool = typer.Option(False, "--two-phase-scan/--no-two-phase-scan", help="Enable two-phase scan (fast candidate pass + deep confirm)"),
    phase1_payload_profile: str = typer.Option("fast", "--phase1-payload-profile", help="Phase1 payload profile: fast, balanced, deep"),
    phase1_max_payloads_per_param: int = typer.Option(2, "--phase1-max-payloads-per-param", min=1, help="Phase1 maximum payload attempts per parameter"),
    phase1_min_score: int = typer.Option(2, "--phase1-min-score", min=0, help="Minimum phase1 score to promote candidate"),
    output: Path = typer.Option(..., "--output", help="JSON output path"),
    markdown: Path | None = typer.Option(None, "--markdown", help="Markdown output path"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose mode"),
    silent: bool = typer.Option(False, "--silent", help="Silent mode"),
    proxy: str | None = typer.Option(None, "--proxy", help="Proxy URL (e.g. http://127.0.0.1:8080)"),
    insecure: bool = typer.Option(False, "--insecure", help="Disable TLS verification"),
    min_score: int = typer.Option(3, "--min-score", help="Minimum score to keep finding"),
) -> None:
    if not url and not list_path:
        raise typer.BadParameter("Provide at least one target via --url or --list.")

    urls = [url] if url else []
    if list_path:
        urls.extend(_read_lines(list_path))
    urls = sorted(set(urls))
    if not urls:
        raise typer.BadParameter("No valid URLs to scan.")

    if ops_profile not in OPS_PROFILE_DEFAULTS:
        raise typer.BadParameter("Invalid --ops-profile. Use one of: recon_fast, balanced, deep_confirm.")
    profile_defaults = OPS_PROFILE_DEFAULTS[ops_profile]
    threads = int(profile_defaults["threads"])
    rate = float(profile_defaults["rate"])
    retries = int(profile_defaults["retries"])
    payload_profile = str(profile_defaults["payload_profile"])
    max_payloads_per_param = int(profile_defaults["max_payloads_per_param"])
    two_phase_scan = bool(profile_defaults["two_phase_scan"])
    phase1_payload_profile = str(profile_defaults["phase1_payload_profile"])
    phase1_max_payloads_per_param = int(profile_defaults["phase1_max_payloads_per_param"])
    phase1_min_score = int(profile_defaults["phase1_min_score"])

    if payload_profile not in {"fast", "balanced", "deep"}:
        raise typer.BadParameter("Invalid --payload-profile. Use one of: fast, balanced, deep.")
    if phase1_payload_profile not in {"fast", "balanced", "deep"}:
        raise typer.BadParameter("Invalid --phase1-payload-profile. Use one of: fast, balanced, deep.")
    profile_names = set(list_wordlist_profiles())
    for profile in wordlist_profile:
        if profile not in profile_names:
            raise typer.BadParameter(f"Invalid --wordlist-profile '{profile}'.")
    profile_paths: list[Path] = []
    for profile in wordlist_profile:
        profile_paths.extend(resolve_wordlist_profile_paths(profile))
    final_wordlist_paths = list(wordlist_path) + profile_paths
    if not final_wordlist_paths:
        raise typer.BadParameter("Provide at least one wordlist via --wordlist or --wordlist-profile.")
    wordlist = prioritize_wordlist(load_wordlists(final_wordlist_paths))
    headers = _parse_headers(header)
    config = ScanConfig(
        urls=urls,
        wordlist=wordlist,
        method=method,
        ops_profile=ops_profile,
        headers=headers,
        threads=threads,
        rate=rate,
        timeout=timeout,
        retries=retries,
        retry_backoff_ms=retry_backoff_ms,
        retry_jitter_ms=retry_jitter_ms,
        payload_profile=payload_profile,
        max_payloads_per_param=max_payloads_per_param,
        early_stop_on_strong_signal=early_stop_on_strong_signal,
        two_phase_scan=two_phase_scan,
        phase1_payload_profile=phase1_payload_profile,
        phase1_max_payloads_per_param=phase1_max_payloads_per_param,
        phase1_min_score=phase1_min_score,
        min_score=min_score,
        verbose=verbose,
        silent=silent,
        proxy=proxy,
        insecure=insecure,
    )
    info(f"Loaded {len(config.urls)} URLs and {len(config.wordlist)} parameters.", silent=config.silent)

    requester = Requester(
        timeout=config.timeout,
        rate=config.rate,
        headers=config.headers,
        proxy=config.proxy,
        verify=not config.insecure,
        max_retries=config.retries,
        retry_backoff_ms=config.retry_backoff_ms,
        retry_jitter_ms=config.retry_jitter_ms,
    )
    try:
        findings, tested_params, request_errors, endpoint_stats, scan_metrics = run_query_miner(
            requester=requester,
            urls=config.urls,
            wordlist=config.wordlist,
            method=config.method,
            headers=config.headers,
            min_score=config.min_score,
            threads=config.threads,
            payload_profile=config.payload_profile,
            max_payloads_per_param=config.max_payloads_per_param,
            early_stop_on_strong_signal=config.early_stop_on_strong_signal,
            two_phase_scan=config.two_phase_scan,
            phase1_payload_profile=config.phase1_payload_profile,
            phase1_max_payloads_per_param=config.phase1_max_payloads_per_param,
            phase1_min_score=config.phase1_min_score,
            progress_callback=lambda current, total: progress(current, total, silent=config.silent),
        )
    finally:
        requester.close()

    summary = ScanSummary(
        target_urls_tested=len(config.urls),
        parameters_tested=tested_params,
        payloads_executed=scan_metrics.get("payloads_executed", 0),
        signals_detected=scan_metrics.get("signals_detected", 0),
        signal_ratio=(
            scan_metrics.get("signals_detected", 0) / scan_metrics.get("payloads_executed", 1)
            if scan_metrics.get("payloads_executed", 0)
            else 0.0
        ),
        findings_confirmed_multi_payload=sum(1 for f in findings if f.signal_hits > 1),
        request_errors=request_errors,
        retry_attempts=requester.retry_attempts,
        elapsed_seconds=scan_metrics.get("elapsed_seconds", 0.0),
        findings_per_minute=(
            (len(findings) * 60.0) / scan_metrics.get("elapsed_seconds", 1.0)
            if scan_metrics.get("elapsed_seconds", 0.0) > 0
            else 0.0
        ),
        parameters_per_minute=(
            (tested_params * 60.0) / scan_metrics.get("elapsed_seconds", 1.0)
            if scan_metrics.get("elapsed_seconds", 0.0) > 0
            else 0.0
        ),
        time_to_first_finding_s=scan_metrics.get("time_to_first_finding_s", 0.0),
        phase1_candidates=scan_metrics.get("phase1_candidates", 0),
        confirmed_findings=len(findings),
        candidates_to_confirmed_ratio=(
            (len(findings) / scan_metrics.get("phase1_candidates", 1))
            if scan_metrics.get("phase1_candidates", 0) > 0
            else 0.0
        ),
        findings=len(findings),
        high=sum(1 for f in findings if f.confidence == Confidence.HIGH),
        medium=sum(1 for f in findings if f.confidence == Confidence.MEDIUM),
        low=sum(1 for f in findings if f.confidence == Confidence.LOW),
    )
    endpoint_confidence = {
        endpoint: {
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for endpoint in endpoint_stats
    }
    for finding in findings:
        if finding.endpoint not in endpoint_confidence:
            endpoint_confidence[finding.endpoint] = {"high": 0, "medium": 0, "low": 0}
        if finding.confidence == Confidence.HIGH:
            endpoint_confidence[finding.endpoint]["high"] += 1
        elif finding.confidence == Confidence.MEDIUM:
            endpoint_confidence[finding.endpoint]["medium"] += 1
        elif finding.confidence == Confidence.LOW:
            endpoint_confidence[finding.endpoint]["low"] += 1

    endpoint_summaries = [
        EndpointSummary(
            endpoint=endpoint,
            parameters_tested=stats.get("parameters_tested", 0),
            payloads_executed=stats.get("payloads_executed", 0),
            signals_detected=stats.get("signals_detected", 0),
            request_errors=stats.get("request_errors", 0),
            retry_attempts=requester.retry_attempts_by_endpoint.get(endpoint, 0),
            findings=stats.get("findings", 0),
            high=endpoint_confidence.get(endpoint, {}).get("high", 0),
            medium=endpoint_confidence.get(endpoint, {}).get("medium", 0),
            low=endpoint_confidence.get(endpoint, {}).get("low", 0),
        )
        for endpoint, stats in sorted(endpoint_stats.items())
    ]
    report = Report(summary=summary, endpoints=endpoint_summaries, findings=findings)
    print_endpoint_metrics(report.endpoints, silent=config.silent)
    print_quick_triage(report, silent=config.silent)
    write_json_report(str(output), report)
    success(f"JSON report written to {output}", silent=config.silent)
    if markdown:
        write_markdown_report(str(markdown), report)
        success(f"Markdown report written to {markdown}", silent=config.silent)
    if not findings:
        warn("No findings above minimum score threshold.", silent=config.silent)
    if request_errors:
        warn(f"Completed with {request_errors} request errors.", silent=config.silent)
