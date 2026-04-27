from pathlib import Path

from typer.testing import CliRunner

from voidminer import cli


runner = CliRunner()


class DummyRequester:
    def __init__(self, *args, **kwargs) -> None:
        self.closed = False
        self.retry_attempts = 0
        self.retry_attempts_by_endpoint = {}

    def close(self) -> None:
        self.closed = True


def test_parse_headers_invalid_format() -> None:
    try:
        cli._parse_headers(["InvalidHeader"])
    except Exception as exc:  # typer.BadParameter
        assert "Invalid header format" in str(exc)
    else:
        raise AssertionError("Expected header parse failure")


def test_cli_requires_url_or_list(tmp_path: Path) -> None:
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("debug\n", encoding="utf-8")
    out = tmp_path / "out.json"
    result = runner.invoke(cli.app, ["--wordlist", str(wordlist), "--output", str(out)])
    assert result.exit_code == 2


def test_cli_runs_with_single_url(monkeypatch, tmp_path: Path) -> None:
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("debug\ntest\n", encoding="utf-8")
    out = tmp_path / "out.json"
    calls: dict[str, int] = {"json": 0}

    def fake_run_query_miner(**kwargs):
        assert kwargs["threads"] == 10
        assert kwargs["min_score"] == 3
        assert kwargs["payload_profile"] == "balanced"
        return [], 2, 0, {"https://example.com/api": {"parameters_tested": 2, "payloads_executed": 6, "signals_detected": 1, "request_errors": 0, "findings": 0}}, {"payloads_executed": 6, "signals_detected": 1}

    def fake_write_json_report(path: str, report) -> None:
        calls["json"] += 1
        assert path == str(out)
        assert report.summary.parameters_tested == 2
        assert len(report.endpoints) == 1

    def fake_print_endpoint_metrics(endpoints, silent=False) -> None:
        calls["table"] = len(endpoints)
        calls["silent"] = int(bool(silent))

    monkeypatch.setattr(cli, "Requester", DummyRequester)
    monkeypatch.setattr(cli, "run_query_miner", fake_run_query_miner)
    monkeypatch.setattr(cli, "write_json_report", fake_write_json_report)
    monkeypatch.setattr(cli, "print_endpoint_metrics", fake_print_endpoint_metrics)
    monkeypatch.setattr(cli, "print_quick_triage", lambda *args, **kwargs: None)

    result = runner.invoke(
        cli.app,
        [
            "--url",
            "https://example.com/api",
            "--wordlist",
            str(wordlist),
            "--output",
            str(out),
            "--ops-profile",
            "balanced",
            "--retries",
            "2",
            "--retry-backoff-ms",
            "50",
            "--retry-jitter-ms",
            "0",
            "--payload-profile",
            "balanced",
            "--max-payloads-per-param",
            "6",
        ],
    )
    assert result.exit_code == 0
    assert calls["json"] == 1
    assert calls["table"] == 1


def test_cli_merges_multiple_wordlists(monkeypatch, tmp_path: Path) -> None:
    w1 = tmp_path / "w1.txt"
    w2 = tmp_path / "w2.txt"
    w1.write_text("debug\ntoken\n", encoding="utf-8")
    w2.write_text("token\ncache\n", encoding="utf-8")
    out = tmp_path / "out.json"
    captured = {"count": 0}

    def fake_run_query_miner(**kwargs):
        captured["count"] = len(kwargs["wordlist"])
        assert "debug" in kwargs["wordlist"]
        assert "token" in kwargs["wordlist"]
        assert "cache" in kwargs["wordlist"]
        return [], 3, 0, {"https://example.com/api": {"parameters_tested": 3, "payloads_executed": 3, "signals_detected": 0, "request_errors": 0, "findings": 0}}, {"payloads_executed": 3, "signals_detected": 0}

    monkeypatch.setattr(cli, "Requester", DummyRequester)
    monkeypatch.setattr(cli, "run_query_miner", fake_run_query_miner)
    monkeypatch.setattr(cli, "write_json_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "print_endpoint_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "print_quick_triage", lambda *args, **kwargs: None)

    result = runner.invoke(
        cli.app,
        [
            "--url",
            "https://example.com/api",
            "--wordlist",
            str(w1),
            "--wordlist",
            str(w2),
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0
    assert captured["count"] == 3


def test_cli_accepts_wordlist_profile(monkeypatch, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    captured = {"has_words": False}

    def fake_run_query_miner(**kwargs):
        captured["has_words"] = len(kwargs["wordlist"]) > 0
        return [], len(kwargs["wordlist"]), 0, {"https://example.com/api": {"parameters_tested": len(kwargs["wordlist"]), "payloads_executed": 1, "signals_detected": 0, "request_errors": 0, "findings": 0}}, {"payloads_executed": 1, "signals_detected": 0}

    monkeypatch.setattr(cli, "Requester", DummyRequester)
    monkeypatch.setattr(cli, "run_query_miner", fake_run_query_miner)
    monkeypatch.setattr(cli, "write_json_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "print_endpoint_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "print_quick_triage", lambda *args, **kwargs: None)

    result = runner.invoke(
        cli.app,
        [
            "--url",
            "https://example.com/api",
            "--wordlist-profile",
            "mixed_recon",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0
    assert captured["has_words"] is True
