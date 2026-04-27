from __future__ import annotations

from pathlib import Path

import typer

from voidminer.config import ScanConfig
from voidminer.models import Confidence, Report, ScanSummary
from voidminer.modes.query_miner import run_query_miner
from voidminer.output.console import info, success, warn
from voidminer.output.json_report import write_json_report
from voidminer.output.markdown_report import write_markdown_report
from voidminer.core.requester import Requester

app = typer.Typer(add_completion=False, help="VoidMiner hidden parameter discovery engine")


def _read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]


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
    wordlist_path: Path = typer.Option(..., "-w", "--wordlist", exists=True, file_okay=True, dir_okay=False, readable=True, help="Parameter wordlist file"),
    header: list[str] = typer.Option([], "-H", "--header", help="Custom header in 'Key: Value' format"),
    method: str = typer.Option("GET", "-X", "--method", help="HTTP method"),
    threads: int = typer.Option(10, "--threads", min=1, help="Worker threads"),
    rate: float = typer.Option(5.0, "--rate", min=0.1, help="Requests per second"),
    timeout: float = typer.Option(10.0, "--timeout", min=0.1, help="HTTP timeout"),
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

    wordlist = _read_lines(wordlist_path)
    headers = _parse_headers(header)
    config = ScanConfig(
        urls=urls,
        wordlist=wordlist,
        method=method,
        headers=headers,
        threads=threads,
        rate=rate,
        timeout=timeout,
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
    )
    try:
        findings, tested_params = run_query_miner(
            requester=requester,
            urls=config.urls,
            wordlist=config.wordlist,
            method=config.method,
            headers=config.headers,
            min_score=config.min_score,
            threads=config.threads,
        )
    finally:
        requester.close()

    summary = ScanSummary(
        target_urls_tested=len(config.urls),
        parameters_tested=tested_params,
        findings=len(findings),
        high=sum(1 for f in findings if f.confidence == Confidence.HIGH),
        medium=sum(1 for f in findings if f.confidence == Confidence.MEDIUM),
        low=sum(1 for f in findings if f.confidence == Confidence.LOW),
    )
    report = Report(summary=summary, findings=findings)
    write_json_report(str(output), report)
    success(f"JSON report written to {output}", silent=config.silent)
    if markdown:
        write_markdown_report(str(markdown), report)
        success(f"Markdown report written to {markdown}", silent=config.silent)
    if not findings:
        warn("No findings above minimum score threshold.", silent=config.silent)
