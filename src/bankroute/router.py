"""End-to-end guarded routing orchestration."""

from __future__ import annotations

import time
import uuid
from typing import Optional

from .catalog import INTENT_CATALOG
from .config import load_thresholds
from .model_service import ModelService
from .openrouter import get_second_opinion
from .safety import assess_and_redact, validate_message
from .schemas import RoutingResult, ToolTrace
from .telemetry import write_audit_event
from .tools import (
    lookup_intent_descriptor,
    resolve_specialist_queue,
    retrieve_labelled_examples,
)


class BankRouter:
    def __init__(self, model_service: Optional[ModelService] = None):
        self.model = model_service or ModelService()

    def route(self, raw_message: object, allow_llm: bool = False) -> RoutingResult:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        message = validate_message(raw_message)
        safety = assess_and_redact(message)
        thresholds = load_thresholds()
        trace = [
            ToolTrace(
                tool="privacy_and_policy_guard",
                status="passed" if not safety.force_review else "review",
                detail=(
                    "PII redacted before external processing; policy and injection patterns checked."
                ),
            )
        ]

        prediction = self.model.predict(safety.redacted, top_k=3)
        trace.append(
            ToolTrace(
                tool="scope_gate",
                status="passed"
                if prediction.scope_probability >= thresholds["scope_threshold"]
                else "out_of_scope",
                detail=f"In-scope probability {prediction.scope_probability:.1%}.",
            )
        )
        top = prediction.top
        descriptor = lookup_intent_descriptor(top.intent)
        trace.append(
            ToolTrace(
                tool="intent_router",
                status="completed",
                detail=(
                    f"Top intent {top.intent} at {top.probability:.1%}; "
                    f"top-two margin {prediction.margin:.1%}."
                ),
            )
        )

        scope_ok = prediction.scope_probability >= thresholds["scope_threshold"]
        confidence_ok = top.probability >= thresholds["intent_confidence_threshold"]
        margin_ok = prediction.margin >= thresholds["intent_margin_threshold"]
        deterministic_accept = scope_ok and confidence_ok and margin_ok and not safety.force_review

        llm_details = None
        llm_used = False
        llm_agrees = False
        if allow_llm and not safety.block_llm and scope_ok and not deterministic_accept:
            opinion = get_second_opinion(safety.redacted, prediction.candidates)
            llm_used = True
            llm_details = opinion.to_dict()
            llm_agrees = (
                opinion.intent == top.intent
                and opinion.confidence >= thresholds["llm_agreement_threshold"]
            )
            trace.append(
                ToolTrace(
                    tool="openrouter_second_opinion",
                    status="agreed" if llm_agrees else "review",
                    detail=(
                        "LLM agreed with the local top intent."
                        if llm_agrees
                        else "LLM unavailable, disagreed, or lacked sufficient confidence."
                    ),
                )
            )

        # The LLM cannot independently override the closed-set model.  Agreement
        # may support an explanation, but a failed deterministic gate remains a
        # human-review decision.
        accepted = deterministic_accept

        # Safety policy has precedence over scope and classification.  A request
        # that asks BankRoute to execute an action or disclose protected data
        # must never be presented merely as an ordinary out-of-scope query.
        if safety.force_review:
            intent = None
            display_name = "Policy review required"
            route_to = "Human Safety Review"
            priority = "urgent"
            explanation = (
                "The message contains a prohibited action/advice request or prompt-injection pattern. "
                "BankRoute does not execute account actions or reveal protected instructions."
            )
            status = "guardrail_review"
        elif not scope_ok:
            intent = None
            display_name = "Outside supported scope"
            route_to = "General Service Triage"
            priority = "review"
            explanation = (
                "This enquiry does not reliably match the ten supported card-payment and ATM intents. "
                "It has been escalated instead of forced into the closest label."
            )
            status = "out_of_scope"
        elif not accepted:
            intent = top.intent
            display_name = str(descriptor["display_name"])
            route_to = "Human Routing Review"
            priority = "review"
            explanation = (
                f"The leading interpretation is {display_name}, but confidence or separation from the "
                "runner-up is below the validated threshold. A service agent must confirm the route."
            )
            status = "low_confidence"
        else:
            queue = resolve_specialist_queue(top.intent)
            examples = retrieve_labelled_examples(top.intent, safety.redacted, k=2)
            trace.append(
                ToolTrace(
                    tool="descriptor_and_example_lookup",
                    status="completed",
                    detail=f"Validated against the descriptor and {len(examples)} nearby labelled examples.",
                )
            )
            intent = top.intent
            display_name = str(descriptor["display_name"])
            route_to = queue["route_to"]
            priority = queue["priority"]
            explanation = str(descriptor["definition"])
            status = "routed"

        result = RoutingResult(
            request_id=request_id,
            original_message=message,
            redacted_message=safety.redacted,
            intent=intent,
            display_name=display_name,
            confidence=round(top.probability, 6),
            route_to=route_to,
            human_review=not accepted,
            decision_status=status,
            explanation=explanation,
            scope_probability=round(prediction.scope_probability, 6),
            priority=priority,
            pii_redacted=safety.pii_redacted,
            safety_flags=safety.flags,
            candidates=prediction.candidates,
            tool_trace=trace,
            llm_used=llm_used,
            llm_details=llm_details,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        write_audit_event(result.to_dict())
        return result
