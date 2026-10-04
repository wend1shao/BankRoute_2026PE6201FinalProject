"""Input guardrails for privacy, prompt injection, and prohibited use.

BankRoute routes service enquiries only.  It never executes transactions,
provides financial advice, or exposes prompts/secrets.  Potential PII is
redacted before an optional external-model call and before local audit logs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .config import MAX_MESSAGE_CHARS, MIN_MESSAGE_CHARS


CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")
ACCOUNT_RE = re.compile(r"\b(?:account|acct)\s*(?:number|no\.?|#)?\s*[:=-]?\s*[A-Z0-9-]{6,}\b", re.I)

INJECTION_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"ignore (?:all |the )?(?:previous|prior|system) instructions",
        r"reveal (?:the )?(?:system prompt|developer message|api key|secret)",
        r"you are now (?:in )?developer mode",
        r"jailbreak",
        r"print (?:the )?(?:environment|env|secret|api key)",
    ]
]

PROHIBITED_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"(?:transfer|send|move)\s+(?:my\s+)?(?:money|funds)",
        r"(?:buy|sell|recommend)\s+(?:a\s+)?(?:stock|fund|crypto|investment)",
        r"(?:approve|reject|decide)\s+(?:my\s+)?(?:loan|credit|mortgage)",
        r"(?:change|reset|reveal)\s+(?:my\s+)?(?:pin|password|passcode)",
    ]
]


@dataclass
class SafetyAssessment:
    original: str
    redacted: str
    pii_redacted: bool
    flags: List[str]
    block_llm: bool
    force_review: bool


def validate_message(message: object) -> str:
    if not isinstance(message, str):
        raise ValueError("message must be a string")
    cleaned = " ".join(message.strip().split())
    if len(cleaned) < MIN_MESSAGE_CHARS:
        raise ValueError(f"message must contain at least {MIN_MESSAGE_CHARS} characters")
    if len(cleaned) > MAX_MESSAGE_CHARS:
        raise ValueError(f"message must contain at most {MAX_MESSAGE_CHARS} characters")
    return cleaned


def assess_and_redact(message: str) -> SafetyAssessment:
    flags: List[str] = []
    redacted = message

    for regex, replacement, flag in [
        (EMAIL_RE, "[EMAIL]", "email_redacted"),
        (ACCOUNT_RE, "[ACCOUNT_ID]", "account_id_redacted"),
        (CARD_RE, "[CARD_NUMBER]", "card_number_redacted"),
        (PHONE_RE, "[PHONE]", "phone_redacted"),
    ]:
        updated, count = regex.subn(replacement, redacted)
        if count:
            flags.append(flag)
        redacted = updated

    injection = any(pattern.search(message) for pattern in INJECTION_PATTERNS)
    if injection:
        flags.append("prompt_injection_detected")

    prohibited = any(pattern.search(message) for pattern in PROHIBITED_PATTERNS)
    if prohibited:
        flags.append("prohibited_action_or_advice_request")

    return SafetyAssessment(
        original=message,
        redacted=redacted,
        pii_redacted=redacted != message,
        flags=flags,
        block_llm=injection or prohibited,
        force_review=injection or prohibited,
    )
