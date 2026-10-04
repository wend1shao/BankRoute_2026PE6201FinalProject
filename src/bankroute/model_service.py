"""Load and query the two-stage scikit-learn routing model.

Stage 1 is a binary scope gate trained on all BANKING77 training rows mapped
to in-scope vs out-of-scope.  Stage 2 is a ten-class intent router trained only
on the selected card-payment and cash-withdrawal intents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

import joblib
import numpy as np

from .catalog import INTENT_CATALOG
from .config import ARTIFACT_DIR
from .schemas import Candidate


@dataclass
class LocalPrediction:
    scope_probability: float
    candidates: List[Candidate]
    margin: float

    @property
    def top(self) -> Candidate:
        return self.candidates[0]


class ModelNotReadyError(RuntimeError):
    pass


class ModelService:
    """Lazy-loading wrapper around the persisted sklearn pipelines."""

    def __init__(self, artifact_dir: Path = ARTIFACT_DIR):
        self.artifact_dir = artifact_dir
        self._scope_gate = None
        self._router = None

    @property
    def ready(self) -> bool:
        return (self.artifact_dir / "scope_gate.joblib").exists() and (
            self.artifact_dir / "intent_router.joblib"
        ).exists()

    def load(self) -> None:
        if not self.ready:
            raise ModelNotReadyError(
                "Model artifacts are missing. Run: python scripts/train.py"
            )
        if self._scope_gate is None:
            self._scope_gate = joblib.load(self.artifact_dir / "scope_gate.joblib")
        if self._router is None:
            self._router = joblib.load(self.artifact_dir / "intent_router.joblib")

    def predict(self, message: str, top_k: int = 3) -> LocalPrediction:
        self.load()
        assert self._scope_gate is not None and self._router is not None

        scope_classes: Sequence[str] = list(self._scope_gate.classes_)
        scope_probs = self._scope_gate.predict_proba([message])[0]
        scope_idx = scope_classes.index("in_scope")
        scope_probability = float(scope_probs[scope_idx])

        probabilities = self._router.predict_proba([message])[0]
        classes: Sequence[str] = list(self._router.classes_)
        order = np.argsort(probabilities)[::-1][:top_k]
        candidates: List[Candidate] = []
        for idx in order:
            label = str(classes[int(idx)])
            descriptor = INTENT_CATALOG[label]
            candidates.append(
                Candidate(
                    intent=label,
                    display_name=str(descriptor["display_name"]),
                    probability=float(probabilities[int(idx)]),
                )
            )
        margin = (
            candidates[0].probability - candidates[1].probability
            if len(candidates) > 1
            else candidates[0].probability
        )
        return LocalPrediction(
            scope_probability=scope_probability,
            candidates=candidates,
            margin=float(margin),
        )

