"""Pipeline de treino: dataset → split → treino → avaliação → payload.

Dados:
- **sintéticos** (curva de Ebbinghaus): dão a forma geral da memória no cold start;
- **reais** (revisões com autoavaliação): valem `real_weight` vezes mais, para a rede
  se ajustar à memória de verdade conforme o histórico cresce.

Splits: treino (ajusta os pesos) · validação (early stopping e champion/challenger)
· teste (número final honesto, a rede nunca o viu).
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from developer_myself.insights.adapters.neural import synthetic
from developer_myself.insights.adapters.neural.features import FEATURE_NAMES, to_features
from developer_myself.insights.adapters.neural.mlp import MLP, Vector, binary_cross_entropy
from developer_myself.insights.application.history import SessionRecord
from developer_myself.insights.application.recommender import ReviewCandidate

DECISION_THRESHOLD = 0.5
LEVEL_RANK = {"BEGINNER": 0, "INTERMEDIATE": 1, "ADVANCED": 2}
MIN_REAL_FOR_REAL_METRICS = 5


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    synthetic_samples: int = 12_000
    hidden: int = 12
    epochs: int = 60
    learning_rate: float = 0.01
    batch_size: int = 32
    l2: float = 1e-4
    patience: int = 6
    real_weight: float = 5.0
    seed: int = 42


@dataclass(slots=True)
class Dataset:
    xs: list[Vector] = field(default_factory=list)
    ts: list[float] = field(default_factory=list)
    ws: list[float] = field(default_factory=list)

    def add(self, candidate: ReviewCandidate, label: float, weight: float) -> None:
        self.xs.append(to_features(candidate))
        self.ts.append(label)
        self.ws.append(weight)

    def __len__(self) -> int:
        return len(self.xs)


@dataclass(slots=True)
class TrainedModel:
    model: MLP
    metrics: dict[str, Any]
    validation: Dataset

    def payload(self) -> dict[str, Any]:
        return {
            "features": FEATURE_NAMES,
            "weights": self.model.to_dict(),
            "metadata": self.metrics,
        }


# --------------------------------------------------------------------------- dados reais


def candidate_from_record(r: SessionRecord) -> ReviewCandidate:
    """Reconstrói as features de ANTES da revisão (o que a rede teria visto)."""
    return ReviewCandidate(
        content_id=r.content_id,
        title=r.content_title,
        days_since_last_session=r.last_contact_days or 0.0,
        points=r.points_before,
        level_rank=LEVEL_RANK.get(r.level_before or "BEGINNER", 0),
        challenges_solved=r.challenges_solved_before,
        review_count=r.review_count_before,
        days_since_first_session=r.days_since_first_session or 0.0,
        last_recall_rating=r.last_recall_rating_before,
        avg_notes_chars=r.avg_notes_chars_before,
    )


def label_from_record(r: SessionRecord) -> float:
    """1 = lembrou (nota 2, 3 ou 4); 0 = esqueceu (nota 1). Convenção do FSRS."""
    return 1.0 if (r.recall_rating or 1) >= 2 else 0.0  # noqa: PLR2004


# --------------------------------------------------------------------------- métricas


def log_loss(preds: list[float], ts: list[float], ws: list[float] | None = None) -> float:
    weights = ws or [1.0] * len(ts)
    total = sum(w * binary_cross_entropy(p, t) for p, t, w in zip(preds, ts, weights, strict=True))
    return total / sum(weights)


def brier(preds: list[float], ts: list[float]) -> float:
    """Erro quadrático da probabilidade: 0 é perfeito, 0.25 é chutar 50%."""
    return sum((p - t) ** 2 for p, t in zip(preds, ts, strict=True)) / len(ts)


def expected_calibration_error(preds: list[float], ts: list[float], bins: int = 10) -> float:
    """Calibração: quando a rede diz 70%, o evento acontece ~70% das vezes?"""
    buckets: list[list[tuple[float, float]]] = [[] for _ in range(bins)]
    for p, t in zip(preds, ts, strict=True):
        buckets[min(int(p * bins), bins - 1)].append((p, t))
    total = len(preds)
    return sum(
        len(b) / total * abs(sum(p for p, _ in b) / len(b) - sum(t for _, t in b) / len(b))
        for b in buckets
        if b
    )


def accuracy(preds: list[float], ts: list[float]) -> float:
    hits = sum((p >= DECISION_THRESHOLD) == (t == 1.0) for p, t in zip(preds, ts, strict=True))
    return hits / len(ts)


def evaluate(model: MLP, data: Dataset) -> float:
    return log_loss([model.predict(x) for x in data.xs], data.ts, data.ws)


# --------------------------------------------------------------------------- treino


def _split[T](
    items: list[T], fractions: tuple[float, float], rng: random.Random
) -> tuple[list[T], ...]:
    shuffled = items[:]
    rng.shuffle(shuffled)
    a = int(len(shuffled) * fractions[0])
    b = a + int(len(shuffled) * fractions[1])
    return shuffled[:a], shuffled[a:b], shuffled[b:]


def train_model(real: list[SessionRecord], config: TrainingConfig | None = None) -> TrainedModel:
    config = config or TrainingConfig()
    rng = random.Random(config.seed)
    synth_train, synth_val, synth_test = _split(
        synthetic.generate(config.synthetic_samples, seed=config.seed), (0.7, 0.15), rng
    )
    real_train, real_val, _ = _split(real, (0.8, 0.2), rng)
    if real and not real_val:  # com pouquíssimos rótulos, valida no próprio treino real
        real_val = real_train[-1:]

    train, val = Dataset(), Dataset()
    real_val_set = Dataset()
    for c, t in synth_train:
        train.add(c, t, 1.0)
    for c, t in synth_val:
        val.add(c, t, 1.0)
    for r in real_train:
        train.add(candidate_from_record(r), label_from_record(r), config.real_weight)
    for r in real_val:
        val.add(candidate_from_record(r), label_from_record(r), config.real_weight)
        real_val_set.add(candidate_from_record(r), label_from_record(r), 1.0)

    model = MLP(n_inputs=len(FEATURE_NAMES), n_hidden=config.hidden, seed=config.seed)
    result = model.fit(
        train.xs,
        train.ts,
        weights=train.ws,
        epochs=config.epochs,
        learning_rate=config.learning_rate,
        batch_size=config.batch_size,
        l2=config.l2,
        validation=(val.xs, val.ts),
        patience=config.patience,
        seed=config.seed,
    )

    test_xs = [to_features(c) for c, _ in synth_test]
    test_ts = [t for _, t in synth_test]
    preds = [model.predict(x) for x in test_xs]
    oracle = [synthetic.true_recall_probability(c) for c, _ in synth_test]
    base_rate = sum(train.ts) / len(train.ts)
    metrics: dict[str, Any] = {
        "trained_at": datetime.now(UTC).isoformat(),
        "trained_on": "synthetic+real" if real else "synthetic",
        "features": len(FEATURE_NAMES),
        "real_samples": len(real),
        "synthetic_samples": config.synthetic_samples,
        "hidden_units": config.hidden,
        "epochs_run": len(result.train_loss),
        "best_epoch": result.best_epoch + 1,
        "stopped_early": result.stopped_early,
        "val_log_loss": round(evaluate(model, val), 4),
        "test_log_loss": round(log_loss(preds, test_ts), 4),
        "baseline_log_loss": round(log_loss([base_rate] * len(test_ts), test_ts), 4),
        "oracle_log_loss": round(log_loss(oracle, test_ts), 4),
        "test_accuracy": round(accuracy(preds, test_ts), 4),
        "test_brier": round(brier(preds, test_ts), 4),
        "test_calibration_error": round(expected_calibration_error(preds, test_ts), 4),
        "mean_abs_error_vs_true_curve": round(
            sum(abs(p - o) for p, o in zip(preds, oracle, strict=True)) / len(oracle), 4
        ),
    }
    if len(real) >= MIN_REAL_FOR_REAL_METRICS:
        real_preds = [model.predict(x) for x in real_val_set.xs]
        metrics["real_val_log_loss"] = round(log_loss(real_preds, real_val_set.ts), 4)
        metrics["real_val_accuracy"] = round(accuracy(real_preds, real_val_set.ts), 4)
    return TrainedModel(model=model, metrics=metrics, validation=val)
