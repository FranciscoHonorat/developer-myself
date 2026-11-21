"""Adapter do port `ReviewRecommender`: degrau 3 (rede neural), com fallback para a regra."""

import json
from pathlib import Path
from typing import Any

from developer_myself.insights.adapters.neural.features import FEATURE_NAMES, to_features
from developer_myself.insights.adapters.neural.mlp import MLP
from developer_myself.insights.application.recommender import (
    ReviewCandidate,
    SpacedRepetitionRule,
)

DEFAULT_MODEL_PATH = Path(__file__).with_name("model.json")


class NeuralReviewRecommender:
    """Degrau 3: MLP treinada (arquivo empacotado ou registro de modelos)."""

    name = "rede-neural"

    def __init__(self, model: MLP, metadata: dict[str, Any], model_id: str | None = None) -> None:
        self._model = model
        self.metadata: dict[str, object] = dict(metadata)
        self.model_id = model_id

    @classmethod
    def from_payload(
        cls, payload: dict[str, Any], model_id: str | None = None
    ) -> NeuralReviewRecommender:
        if tuple(payload["features"]) != FEATURE_NAMES:
            raise ValueError("O modelo foi treinado com outras features. Treine de novo.")
        return cls(MLP.from_dict(payload["weights"]), payload["metadata"], model_id)

    @classmethod
    def load(cls, path: Path = DEFAULT_MODEL_PATH) -> NeuralReviewRecommender:
        return cls.from_payload(json.loads(path.read_text()), model_id=f"arquivo:{path.name}")

    def recall_probability(self, candidate: ReviewCandidate) -> float:
        return self._model.predict(to_features(candidate))


def load_best_recommender(
    path: Path = DEFAULT_MODEL_PATH,
) -> NeuralReviewRecommender | SpacedRepetitionRule:
    """Usa a rede se houver modelo treinado; senão cai para a regra (o domínio não muda)."""
    try:
        return NeuralReviewRecommender.load(path)
    except FileNotFoundError, ValueError, KeyError:
        return SpacedRepetitionRule()
