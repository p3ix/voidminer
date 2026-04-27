from pathlib import Path

from typer.testing import CliRunner

from voidminer import cli


runner = CliRunner()


class DummyRequester:
    def __init__(self, *args, **kwargs) -> None:
        self.closed = False

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
    assert result.exit_code != 0
    assert "Provide at least one target via --url or --list." in result.stdout


def test_cli_runs_with_single_url(monkeypatch, tmp_path: Path) -> None:
    wordlist = tmp_path / "wordlist.txt"
    wordlist.write_text("debug\ntest\n", encoding="utf-8")
    out = tmp_path / "out.json"
    calls: dict[str, int] = {"json": 0}

    def fake_run_query_miner(**kwargs):
        assert kwargs["threads"] == 4
        assert kwargs["min_score"] == 3
        return [], 2

    def fake_write_json_report(path: str, report) -> None:
        calls["json"] += 1
        assert path == str(out)
        assert report.summary.parameters_tested == 2

    monkeypatch.setattr(cli, "Requester", DummyRequester)
    monkeypatch.setattr(cli, "run_query_miner", fake_run_query_miner)
    monkeypatch.setattr(cli, "write_json_report", fake_write_json_report)

    result = runner.invoke(
        cli.app,
        [
            "--url",
            "https://example.com/api",
            "--wordlist",
            str(wordlist),
            "--output",
            str(out),
            "--threads",
            "4",
        ],
    )
    assert result.exit_code == 0
    assert calls["json"] == 1
