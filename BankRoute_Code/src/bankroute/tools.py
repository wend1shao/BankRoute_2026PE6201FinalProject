"""Deterministic tools used by the routing pipeline.

These tools keep business logic outside the LLM: descriptors define meanings,
examples ground explanations, queue lookup is closed and deterministic, and
cost calculation is arithmetic rather than generated text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from .catalog import INTENT_CATALOG, descriptor_for
from .config import ARTIFACT_DIR


TOKEN_RE = re.compile(r"[a-z0-9]+")


TOOL_DESCRIPTORS = [
    {
        "name": "lookup_intent_descriptor",
        "purpose": "Return the approved meaning, exclusions, route, and priority for one supported intent.",
        "input": {"intent": "one closed-vocabulary intent label"},
        "output": "descriptor object",
    },
    {
        "name": "retrieve_labelled_examples",
        "purpose": "Retrieve nearby labelled training examples for evidence and debugging.",
        "input": {"intent": "supported label", "query": "redacted customer message", "k": "1-5"},
        "output": "labelled example strings",
    },
    {
        "name": "resolve_specialist_queue",
        "purpose": "Map an approved intent to a fixed specialist queue; never executes an account action.",
        "input": {"intent": "supported label"},
        "output": "queue and priority",
    },
    {
        "name": "estimate_llm_cost",
        "purpose": "Calculate estimated model-call cost from token counts and stated prices.",
        "input": {"input_tokens": "integer", "output_tokens": "integer", "prices_per_million": "numbers"},
        "output": "estimated USD cost",
    },
]


def lookup_intent_descriptor(intent: str) -> Dict[str, object]:
    return descriptor_for(intent)


def resolve_specialist_queue(intent: str) -> Dict[str, str]:
    descriptor = descriptor_for(intent)
    return {
        "route_to": str(descriptor["route_to"]),
        "priority": str(descriptor["priority"]),
    }


def _tokens(value: str) -> set:
    return set(TOKEN_RE.findall(value.lower()))


def retrieve_labelled_examples(intent: str, query: str, k: int = 3) -> List[str]:
    if intent not in INTENT_CATALOG:
        return []
    path = ARTIFACT_DIR / "examples.json"
    if not path.exists():
        return []
    examples = json.loads(path.read_text(encoding="utf-8")).get(intent, [])
    q = _tokens(query)
    scored = []
    for example in examples:
        e = _tokens(example)
        union = q | e
        score = len(q & e) / len(union) if union else 0.0
        scored.append((score, example))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [example for _, example in scored[: max(1, min(k, 5))]]


def estimate_llm_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: float = 0.15,
    output_price_per_million: float = 0.60,
) -> float:
    return round(
        (input_tokens / 1_000_000) * input_price_per_million
        + (output_tokens / 1_000_000) * output_price_per_million,
        8,
    )

