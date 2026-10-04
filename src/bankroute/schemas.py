"""Typed result objects and strict serialization for the routing pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Candidate:
    intent: str
    display_name: str
    probability: float


@dataclass
class ToolTrace:
    tool: str
    status: str
    detail: str


@dataclass
class RoutingResult:
    request_id: str
    original_message: str
    redacted_message: str
    intent: Optional[str]
    display_name: str
    confidence: float
    route_to: str
    human_review: bool
    decision_status: str
    explanation: str
    scope_probability: float
    priority: str = "standard"
    pii_redacted: bool = False
    safety_flags: List[str] = field(default_factory=list)
    candidates: List[Candidate] = field(default_factory=list)
    tool_trace: List[ToolTrace] = field(default_factory=list)
    llm_used: bool = False
    llm_details: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

