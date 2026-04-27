# Usage

MVP command:

`voidminer -l urls.txt -w data/params_base.txt --output results.json`

You can repeat `-w/--wordlist` to merge multiple files (deduplicated at runtime):

`voidminer -u https://target -w data/params_base.txt -w data/params_cache_cdn.txt --output results.json`

You can also use predefined wordlist profiles:

`voidminer -u https://target --wordlist-profile mixed_recon --output results.json`

Use `--markdown report.md` to also export Markdown findings.

Multi-payload options:

- `--payload-profile fast|balanced|deep`
- `--max-payloads-per-param N`
- `--early-stop-on-strong-signal` (default) / `--no-early-stop-on-strong-signal`

Throughput profiles:

- `--ops-profile recon_fast|balanced|deep_confirm`
- `--two-phase-scan` for candidate-first pipeline
- Phase1 tuning: `--phase1-payload-profile`, `--phase1-max-payloads-per-param`, `--phase1-min-score`
