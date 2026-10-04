#!/usr/bin/env python3
"""Evaluate the rented foundation model on a frozen 50-query sample.

The API key stays in the process environment.  It is never written to a file,
printed, or included in a request result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankroute.catalog import IN_SCOPE_LABELS, INTENT_CATALOG  # noqa: E402
from bankroute.config import RAW_DATA_DIR, openrouter_key_available, openrouter_model  # noqa: E402
from bankroute.openrouter import get_second_opinion  # noqa: E402
from bankroute.schemas import Candidate  # noqa: E402


def main() -> None:
    if not openrouter_key_available():
        raise SystemExit("OPENROUTER_API_KEY is unavailable; no external calls were made.")

    test = pd.read_csv(RAW_DATA_DIR / "test.csv")
    frozen = (
        test[test.category.isin(IN_SCOPE_LABELS)]
        .groupby("category", group_keys=False)
        .sample(n=5, random_state=6201)
        .sort_values(["category", "text"])
        .reset_index(drop=True)
    )
    candidates = [
        Candidate(intent=label, display_name=str(INTENT_CATALOG[label]["display_name"]), probability=0.0)
        for label in IN_SCOPE_LABELS
    ]
    rows = []
    for index, row in frozen.iterrows():
        opinion = get_second_opinion(row.text, candidates)
        rows.append(
            {
                "sample_id": int(index),
                "expected_intent": row.category,
                "predicted_intent": opinion.intent,
                "confidence": opinion.confidence,
                "json_valid_and_label_allowed": opinion.error is None and opinion.intent in IN_SCOPE_LABELS,
                "latency_ms": opinion.latency_ms,
                "input_tokens": opinion.input_tokens,
                "output_tokens": opinion.output_tokens,
                "estimated_cost_usd": opinion.estimated_cost_usd,
                "error": opinion.error,
            }
        )
        print(f"Completed {index + 1}/{len(frozen)}", flush=True)

    predictions = [row["predicted_intent"] or "__abstain__" for row in rows]
    truth = [row["expected_intent"] for row in rows]
    summary = {
        "evaluation": "OpenRouter foundation-model comparison on frozen official-test sample",
        "model": openrouter_model(),
        "sample_rows": len(rows),
        "sampling": "5 official test examples per each of 10 in-scope labels; random_state=6201",
        "accuracy": round(float(accuracy_score(truth, predictions)), 6),
        "macro_f1": round(float(f1_score(truth, predictions, labels=IN_SCOPE_LABELS, average="macro", zero_division=0)), 6),
        "schema_and_allowed_label_success": round(sum(row["json_valid_and_label_allowed"] for row in rows) / len(rows), 6),
        "mean_latency_ms": round(sum(row["latency_ms"] for row in rows) / len(rows), 2),
        "total_input_tokens": sum(row["input_tokens"] for row in rows),
        "total_output_tokens": sum(row["output_tokens"] for row in rows),
        "estimated_total_cost_usd": round(sum(row["estimated_cost_usd"] for row in rows), 6),
        "errors": sum(row["error"] is not None for row in rows),
        "secret_handling": "API key read from environment only; never persisted or returned.",
    }
    results = ROOT / "evals" / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "openrouter_eval_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(results / "openrouter_predictions.csv", index=False)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

