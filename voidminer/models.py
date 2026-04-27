from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Location(str, Enum):
    QUERY = "query"
    JSON = "json"
    HEADER = "header"
    FORM = "form"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Evidence(BaseModel):
    status_changed: bool = False
    length_delta: int = 0
    reflected: bool = False
    new_headers: list[str] = Field(default_factory=list)
    removed_headers: list[str] = Field(default_factory=list)
    new_json_keys: list[str] = Field(default_factory=list)
    removed_json_keys: list[str] = Field(default_factory=list)
    timing_delta_ms: float = 0.0
    body_hash_changed: bool = False
    technical_error: bool = False
    auth_bypass_signal: bool = False


class RequestSnapshot(BaseModel):
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None


class ResponseSnapshot(BaseModel):
    status_code: int
    content_length: int
    response_time_ms: float
    sample: str


class Finding(BaseModel):
    endpoint: str
    method: str
    parameter: str
    location: Location
    payload: str
    payloads_tested: list[str] = Field(default_factory=list)
    payloads_with_signal: list[str] = Field(default_factory=list)
    payloads_executed: int = 0
    signal_hits: int = 0
    confidence: Confidence
    score: int
    evidence: Evidence
    evidence_by_payload: dict[str, Evidence] = Field(default_factory=dict)
    request: RequestSnapshot
    response: ResponseSnapshot


class BaselineFingerprint(BaseModel):
    status_code: int
    content_length: int
    body_hash: str
    header_hash: str
    response_time_ms: float
    headers: list[str] = Field(default_factory=list)
    json_keys: list[str] = Field(default_factory=list)
    html_title: str | None = None
    html_forms: int = 0
    html_input_names: list[str] = Field(default_factory=list)


class DiffResult(BaseModel):
    evidence: Evidence
    response: ResponseSnapshot
    status_code_before: int
    status_code_after: int
    content_length_before: int
    content_length_after: int


class ScanSummary(BaseModel):
    target_urls_tested: int = 0
    parameters_tested: int = 0
    payloads_executed: int = 0
    signals_detected: int = 0
    signal_ratio: float = 0.0
    findings_confirmed_multi_payload: int = 0
    request_errors: int = 0
    retry_attempts: int = 0
    elapsed_seconds: float = 0.0
    findings_per_minute: float = 0.0
    parameters_per_minute: float = 0.0
    time_to_first_finding_s: float = 0.0
    phase1_candidates: int = 0
    confirmed_findings: int = 0
    candidates_to_confirmed_ratio: float = 0.0
    findings: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class EndpointSummary(BaseModel):
    endpoint: str
    parameters_tested: int = 0
    payloads_executed: int = 0
    signals_detected: int = 0
    request_errors: int = 0
    retry_attempts: int = 0
    findings: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class Report(BaseModel):
    summary: ScanSummary
    endpoints: list[EndpointSummary] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
