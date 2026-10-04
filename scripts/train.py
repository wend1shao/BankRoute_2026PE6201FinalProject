#!/usr/bin/env python3
"""Train the two-stage TF-IDF + logistic-regression BankRoute models.

Thresholds are selected only on a stratified 20% split of the official training
data.  The official test split remains untouched until final evaluation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bankroute.catalog import IN_SCOPE_LABELS  # noqa: E402
from bankroute.config import ARTIFACT_DIR, RAW_DATA_DIR  # noqa: E402


SEED = 42


def features() -> FeatureUnion:
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.98,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    max_features=35_000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )


def classifier() -> Pipeline:
    return Pipeline(
        [
            ("features", features()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2_000,
                    class_weight="balanced",
                    random_state=SEED,
                ),
            ),
        ]
    )


def candidate_arrays(router: Pipeline, texts: pd.Series):
    probs = router.predict_proba(texts)
    order = np.argsort(probs, axis=1)[:, ::-1]
    classes = np.asarray(router.classes_)
    top_labels = classes[order[:, 0]]
    top_probs = probs[np.arange(len(probs)), order[:, 0]]
    second_probs = probs[np.arange(len(probs)), order[:, 1]]
    return top_labels, top_probs, top_probs - second_probs


def select_thresholds(scope_gate: Pipeline, router: Pipeline, validation: pd.DataFrame):
    scope_probs = scope_gate.predict_proba(validation.text)[:, list(scope_gate.classes_).index("in_scope")]
    top_labels, top_probs, margins = candidate_arrays(router, validation.text)
    is_in = validation.category.isin(IN_SCOPE_LABELS).to_numpy()
    y_true = validation.category.to_numpy()

    best = None
    all_results = []
    for scope_threshold in np.arange(0.45, 0.86, 0.05):
        for confidence_threshold in np.arange(0.35, 0.81, 0.05):
            for margin_threshold in np.arange(0.02, 0.31, 0.04):
                accept = (
                    (scope_probs >= scope_threshold)
                    & (top_probs >= confidence_threshold)
                    & (margins >= margin_threshold)
                )
                safe_oos = float((~accept[~is_in]).mean())
                in_coverage = float(accept[is_in].mean())
                accepted_accuracy = (
                    float(accuracy_score(y_true[is_in][accept[is_in]], top_labels[is_in][accept[is_in]]))
                    if accept[is_in].any()
                    else 0.0
                )
                scored_predictions = np.where(accept[is_in], top_labels[is_in], "__abstain__")
                macro_f1 = float(
                    f1_score(
                        y_true[is_in],
                        scored_predictions,
                        labels=IN_SCOPE_LABELS,
                        average="macro",
                        zero_division=0,
                    )
                )
                # Reward safety, useful coverage, and correct accepted routes.
                score = 0.45 * safe_oos + 0.30 * macro_f1 + 0.15 * in_coverage + 0.10 * accepted_accuracy
                row = {
                    "scope_threshold": round(float(scope_threshold), 2),
                    "intent_confidence_threshold": round(float(confidence_threshold), 2),
                    "intent_margin_threshold": round(float(margin_threshold), 2),
                    "validation_oos_safe_escalation": round(safe_oos, 6),
                    "validation_in_scope_coverage": round(in_coverage, 6),
                    "validation_selective_accuracy": round(accepted_accuracy, 6),
                    "validation_macro_f1_with_abstention": round(macro_f1, 6),
                    "selection_score": round(score, 6),
                }
                all_results.append(row)
                feasible = safe_oos >= 0.90 and macro_f1 >= 0.75 and in_coverage >= 0.60
                if feasible and (best is None or score > best[0]):
                    best = (score, row)

    if best is None:
        best_row = max(all_results, key=lambda x: x["selection_score"])
    else:
        best_row = best[1]
    best_row["llm_agreement_threshold"] = 0.75
    return best_row


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(RAW_DATA_DIR / "train.csv")
    if len(train) != 10_003 or train.category.nunique() != 77:
        raise ValueError("Unexpected BANKING77 training data shape")

    fit, validation = train_test_split(
        train,
        test_size=0.20,
        random_state=SEED,
        stratify=train.category,
    )
    fit = fit.reset_index(drop=True)
    validation = validation.reset_index(drop=True)

    dev_scope = classifier()
    dev_scope.fit(
        fit.text,
        np.where(fit.category.isin(IN_SCOPE_LABELS), "in_scope", "out_of_scope"),
    )
    fit_in = fit[fit.category.isin(IN_SCOPE_LABELS)]
    dev_router = classifier()
    dev_router.fit(fit_in.text, fit_in.category)
    thresholds = select_thresholds(dev_scope, dev_router, validation)

    final_scope = classifier()
    final_scope.fit(
        train.text,
        np.where(train.category.isin(IN_SCOPE_LABELS), "in_scope", "out_of_scope"),
    )
    train_in = train[train.category.isin(IN_SCOPE_LABELS)]
    final_router = classifier()
    final_router.fit(train_in.text, train_in.category)

    joblib.dump(final_scope, ARTIFACT_DIR / "scope_gate.joblib")
    joblib.dump(final_router, ARTIFACT_DIR / "intent_router.joblib")
    (ARTIFACT_DIR / "thresholds.json").write_text(
        json.dumps(thresholds, indent=2), encoding="utf-8"
    )

    examples = {
        label: train_in[train_in.category == label].text.tolist()
        for label in IN_SCOPE_LABELS
    }
    (ARTIFACT_DIR / "examples.json").write_text(
        json.dumps(examples, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "official_train_rows": len(train),
        "official_test_rows_expected": 3_080,
        "all_categories": int(train.category.nunique()),
        "in_scope_labels": IN_SCOPE_LABELS,
        "in_scope_train_rows": len(train_in),
        "out_of_scope_labels": int(train.category.nunique() - len(IN_SCOPE_LABELS)),
        "validation_rows": len(validation),
        "threshold_selection": thresholds,
        "model_family": "TF-IDF word+character features with logistic regression",
        "sklearn_version": __import__("sklearn").__version__,
    }
    (ARTIFACT_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

