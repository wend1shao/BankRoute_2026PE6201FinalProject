"""Transparent non-AI keyword baseline required by the project rubric."""

from __future__ import annotations

import re
from typing import Optional


def predict_keyword(message: str) -> Optional[str]:
    text = message.lower()
    is_cash = bool(re.search(r"\b(atm|cash|withdraw|withdrew|money out)\b", text))
    is_card = bool(re.search(r"\b(card|merchant|purchase|shop|store|payment)\b", text))

    if re.search(r"\b(didn.t|did not|don.t|do not|not me|unrecogn|unknown|random)\b", text):
        if is_cash:
            return "cash_withdrawal_not_recognised"
        if is_card:
            return "card_payment_not_recognised"
    if "pending" in text or "taking too long" in text or "not completed" in text:
        if is_cash:
            return "pending_cash_withdrawal"
        if is_card:
            return "pending_card_payment"
    if re.search(r"\b(declin|reject|blocked|wouldn.t work|won.t work)\b", text):
        if is_cash:
            return "declined_cash_withdrawal"
        if is_card:
            return "declined_card_payment"
    if re.search(r"\b(exchange rate|conversion rate|currency rate)\b", text):
        if is_cash:
            return "wrong_exchange_rate_for_cash_withdrawal"
        if is_card:
            return "card_payment_wrong_exchange_rate"
    if re.search(r"\b(fee|charge|charged extra|commission)\b", text):
        if is_cash:
            return "cash_withdrawal_charge"
        if is_card:
            return "card_payment_fee_charged"
    return None

