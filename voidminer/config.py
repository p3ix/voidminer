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
    min_score: int = 3
    verbose: bool = False
    silent: bool = False
    proxy: str | None = None
    insecure: bool = False
