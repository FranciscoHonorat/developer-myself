"""Adapters do port `ReviewRecommender`: degrau 1 (regra) e degrau 3 (rede neural)."""

import json
import math
from pathlib import Path
from typing import Any

from developer_myself.insights.adapters.neural.features import FEATURE_NAMES, to_features
from developer_myself.insights.adapters.neural.mlp import MLP
from developer_myself.insights.application.recommender import ReviewCandidate

DEFAULT_MODEL_PATH = Path(__file__).with_name("model.json")


class SpacedRepetitionRule:
    """Degrau 1: regra fixa, funciona sem dado nenhum. Serve de fallback."""

    name = "regra"

    def __init__(self) -> None:
        self.metadata: dict[str, object] = {}

    def recall_probability(self, candidate: ReviewCandidate) -> float:
        interval = 2.0 ** (1 + candidate.level_rank) + candidate.points / 5
        return math.exp(-candidate.days_since_last_session / interval)


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
