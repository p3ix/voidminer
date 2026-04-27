from __future__ import annotations

from pydantic import BaseModel, Field


class ScanConfig(BaseModel):
    urls: list[str]
    wordlist: list[str]
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    threads: int = 10
    rate: float = 5.0
    timeout: float = 10.0
    retries: int = 0
    retry_backoff_ms: float = 200.0
    retry_jitter_ms: float = 100.0
    ops_profile: str = "balanced"
    payload_profile: str = "balanced"
    max_payloads_per_param: int = 6
    early_stop_on_strong_signal: bool = True
    two_phase_scan: bool = False
    phase1_payload_profile: str = "fast"
    phase1_max_payloads_per_param: int = 2
    phase1_min_score: int = 2
    min_score: int = 3
    verbose: bool = False
    silent: bool = False
    proxy: str | None = None
    insecure: bool = False
