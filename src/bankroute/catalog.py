"""Closed intent vocabulary, descriptors, exclusions, and queue mappings.

The descriptors are product logic, not model output.  They define the exact
meaning of each supported route and make LLM prompts and UI explanations
auditable.  The ten labels deliberately form five difficult card-vs-ATM pairs.
"""

from __future__ import annotations

from typing import Dict, List


INTENT_CATALOG: Dict[str, Dict[str, object]] = {
    "card_payment_not_recognised": {
        "display_name": "Unrecognised card payment",
        "definition": "A merchant card purchase appears in the account and the customer says they did not make or recognise it.",
        "positive_cues": ["unknown merchant", "card charge I did not make", "payment I do not recognise"],
        "exclude": ["cash or ATM withdrawal", "known payment still pending", "card payment fee"],
        "route_to": "Card Payment Disputes",
        "priority": "urgent",
    },
    "cash_withdrawal_not_recognised": {
        "display_name": "Unrecognised cash withdrawal",
        "definition": "An ATM or cash withdrawal appears in the account and the customer says they did not make it.",
        "positive_cues": ["cash withdrawal I did not make", "unknown ATM withdrawal", "cash taken from account"],
        "exclude": ["merchant card purchase", "withdrawal still pending", "ATM fee"],
        "route_to": "ATM Cash Disputes",
        "priority": "urgent",
    },
    "pending_card_payment": {
        "display_name": "Pending card payment",
        "definition": "A card purchase made by the customer remains pending or incomplete.",
        "positive_cues": ["purchase still pending", "card payment has not completed", "merchant payment pending"],
        "exclude": ["ATM withdrawal pending", "payment declined", "unknown payment"],
        "route_to": "Card Payment Operations",
        "priority": "standard",
    },
    "pending_cash_withdrawal": {
        "display_name": "Pending cash withdrawal",
        "definition": "An ATM cash withdrawal made or attempted by the customer remains pending.",
        "positive_cues": ["ATM withdrawal pending", "cash withdrawal not completed", "cash received but transaction pending"],
        "exclude": ["card purchase pending", "ATM withdrawal declined", "unknown withdrawal"],
        "route_to": "ATM Cash Operations",
        "priority": "standard",
    },
    "declined_card_payment": {
        "display_name": "Declined card payment",
        "definition": "A merchant card purchase was rejected or the card would not work at checkout.",
        "positive_cues": ["card declined in store", "payment rejected", "card would not work for purchase"],
        "exclude": ["ATM cash withdrawal declined", "entire card not working in every context", "payment pending"],
        "route_to": "Card Payment Operations",
        "priority": "standard",
    },
    "declined_cash_withdrawal": {
        "display_name": "Declined cash withdrawal",
        "definition": "An ATM rejected the customer's attempt to withdraw cash.",
        "positive_cues": ["ATM declined", "cash would not come out", "withdrawal rejected"],
        "exclude": ["merchant card payment declined", "withdrawal pending", "unrecognised withdrawal"],
        "route_to": "ATM Cash Operations",
        "priority": "standard",
    },
    "card_payment_wrong_exchange_rate": {
        "display_name": "Wrong exchange rate on card payment",
        "definition": "The customer disputes the currency exchange rate applied to a merchant card purchase.",
        "positive_cues": ["purchase exchange rate wrong", "card payment abroad overcharged", "merchant conversion rate"],
        "exclude": ["ATM exchange rate", "separate card payment fee", "general exchange-rate enquiry"],
        "route_to": "Card FX Review",
        "priority": "standard",
    },
    "wrong_exchange_rate_for_cash_withdrawal": {
        "display_name": "Wrong exchange rate on cash withdrawal",
        "definition": "The customer disputes the currency exchange rate applied to an ATM cash withdrawal.",
        "positive_cues": ["ATM conversion rate wrong", "cash abroad exchange rate", "withdrawal currency conversion"],
        "exclude": ["merchant card exchange rate", "separate ATM fee", "general exchange-rate enquiry"],
        "route_to": "ATM FX Review",
        "priority": "standard",
    },
    "card_payment_fee_charged": {
        "display_name": "Fee charged for card payment",
        "definition": "A separate fee was charged for making a merchant card payment.",
        "positive_cues": ["fee for using card", "extra card transaction charge", "merchant payment fee"],
        "exclude": ["ATM withdrawal fee", "wrong currency exchange rate", "unknown merchant payment"],
        "route_to": "Card Fees Review",
        "priority": "standard",
    },
    "cash_withdrawal_charge": {
        "display_name": "Fee charged for cash withdrawal",
        "definition": "A separate fee was charged for withdrawing cash from an ATM.",
        "positive_cues": ["ATM fee", "cash withdrawal charge", "charged to take out money"],
        "exclude": ["card purchase fee", "wrong ATM exchange rate", "unknown cash withdrawal"],
        "route_to": "ATM Fees Review",
        "priority": "standard",
    },
}

IN_SCOPE_LABELS: List[str] = list(INTENT_CATALOG)
ALLOWED_ROUTES = sorted({str(v["route_to"]) for v in INTENT_CATALOG.values()})


def descriptor_for(intent: str) -> Dict[str, object]:
    """Return a copy so callers cannot mutate the product vocabulary."""

    if intent not in INTENT_CATALOG:
        raise KeyError(f"Unknown intent: {intent}")
    return dict(INTENT_CATALOG[intent])


def compact_descriptor(intent: str) -> str:
    item = INTENT_CATALOG[intent]
    cues = "; ".join(str(x) for x in item["positive_cues"])
    exclusions = "; ".join(str(x) for x in item["exclude"])
    return (
        f"{intent}: {item['definition']} Positive cues: {cues}. "
        f"Do not use for: {exclusions}."
    )

