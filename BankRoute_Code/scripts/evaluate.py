#!/usr/bin/env python3
"""Evaluate the keyword baseline, closed-set model, and guarded router."""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankroute.catalog import IN_SCOPE_LABELS  # noqa: E402
from bankroute.config import ARTIFACT_DIR, EVAL_DIR, RAW_DATA_DIR, load_thresholds  # noqa: E402
from bankroute.keyword_baseline import predict_keyword  # noqa: E402


def main() -> None:
    test = pd.read_csv(RAW_DATA_DIR / "test.csv")
    if len(test) != 3_080 or test.category.nunique() != 77:
        raise ValueError("Unexpected BANKING77 test data shape")

    scope_gate = joblib.load(ARTIFACT_DIR / "scope_gate.joblib")
    router = joblib.load(ARTIFACT_DIR / "intent_router.joblib")
    thresholds = load_thresholds()
    in_mask = test.category.isin(IN_SCOPE_LABELS).to_numpy()
    in_test = test[in_mask].copy()
    oos_test = test[~in_mask].copy()

    keyword_predictions = [predict_keyword(text) or "__abstain__" for text in in_test.text]
    keyword_macro_f1 = f1_score(
        in_test.category,
        keyword_predictions,
        labels=IN_SCOPE_LABELS,
        average="macro",
        zero_division=0,
    )

    started = time.perf_counter()
    intent_probs = router.predict_proba(test.text)
    elapsed = time.perf_counter() - started
    intent_classes = np.asarray(router.classes_)
    order = np.argsort(intent_probs, axis=1)[:, ::-1]
    top_labels = intent_classes[order[:, 0]]
    top_probs = intent_probs[np.arange(len(test)), order[:, 0]]
    second_probs = intent_probs[np.arange(len(test)), order[:, 1]]
    margins = top_probs - second_probs

    scope_probs = scope_gate.predict_proba(test.text)[:, list(scope_gate.classes_).index("in_scope")]
    accept = (
        (scope_probs >= thresholds["scope_threshold"])
        & (top_probs >= thresholds["intent_confidence_threshold"])
        & (margins >= thresholds["intent_margin_threshold"])
    )

    closed_set_accuracy = accuracy_score(in_test.category, top_labels[in_mask])
    closed_set_macro_f1 = f1_score(
        in_test.category, top_labels[in_mask], labels=IN_SCOPE_LABELS, average="macro"
    )
    guarded_predictions = np.where(accept[in_mask], top_labels[in_mask], "__abstain__")
    guarded_macro_f1 = f1_score(
        in_test.category,
        guarded_predictions,
        labels=IN_SCOPE_LABELS,
        average="macro",
        zero_division=0,
    )
    in_coverage = float(accept[in_mask].mean())
    selective_accuracy = float(
        accuracy_score(in_test.category.to_numpy()[accept[in_mask]], top_labels[in_mask][accept[in_mask]])
    )
    oos_safe = float((~accept[~in_mask]).mean())
    false_route_rate = float(accept[~in_mask].mean())

    metrics = {
        "dataset": {
            "official_test_rows": len(test),
            "in_scope_rows": len(in_test),
            "out_of_scope_rows": len(oos_test),
            "in_scope_labels": IN_SCOPE_LABELS,
            "out_of_scope_label_count": int(oos_test.category.nunique()),
        },
        "non_ai_keyword_baseline": {
            "macro_f1": round(float(keyword_macro_f1), 6),
            "coverage": round(float(np.mean(np.asarray(keyword_predictions) != "__abstain__")), 6),
        },
        "tfidf_logistic_closed_set": {
            "accuracy": round(float(closed_set_accuracy), 6),
            "macro_f1": round(float(closed_set_macro_f1), 6),
            "mean_latency_ms_per_query_batch": round(elapsed * 1000 / len(test), 4),
        },
        "guarded_router": {
            "macro_f1_with_abstention": round(float(guarded_macro_f1), 6),
            "in_scope_coverage": round(in_coverage, 6),
            "selective_accuracy": round(selective_accuracy, 6),
            "out_of_scope_safe_escalation": round(oos_safe, 6),
            "out_of_scope_false_route_rate": round(false_route_rate, 6),
            "thresholds": thresholds,
        },
    }

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    results_dir = EVAL_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "evaluation_summary.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    report = classification_report(
        in_test.category,
        top_labels[in_mask],
        labels=IN_SCOPE_LABELS,
        output_dict=True,
        zero_division=0,
    )
    rows = []
    for label in IN_SCOPE_LABELS:
        rows.append({"intent": label, **report[label]})
    pd.DataFrame(rows).to_csv(results_dir / "per_intent_metrics.csv", index=False)

    matrix = confusion_matrix(in_test.category, top_labels[in_mask], labels=IN_SCOPE_LABELS)
    matrix_df = pd.DataFrame(matrix, index=IN_SCOPE_LABELS, columns=IN_SCOPE_LABELS)
    matrix_df.to_csv(results_dir / "confusion_matrix.csv")

    prediction_rows = test.copy()
    prediction_rows["predicted_intent"] = top_labels
    prediction_rows["intent_confidence"] = top_probs
    prediction_rows["scope_probability"] = scope_probs
    prediction_rows["margin"] = margins
    prediction_rows["accepted"] = accept
    prediction_rows.to_csv(results_dir / "official_test_predictions.csv", index=False)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

