"""Testes da rede neural: a matemática primeiro, depois treino, retreino e recarga."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

from developer_myself.insights.adapters.memory.model_registry import InMemoryModelRegistry
from developer_myself.insights.adapters.memory.store import InMemorySessionHistoryStore
from developer_myself.insights.adapters.neural.features import FEATURE_NAMES, to_features
from developer_myself.insights.adapters.neural.mlp import (
    MLP,
    Adam,
    binary_cross_entropy,
    sigmoid,
)
from developer_myself.insights.adapters.neural.provider import RecommenderProvider
from developer_myself.insights.adapters.neural.recommender import (
    NeuralReviewRecommender,
    load_best_recommender,
)
from developer_myself.insights.adapters.neural.retrain import RetrainJob
from developer_myself.insights.adapters.neural.training import (
    Dataset,
    TrainingConfig,
    brier,
    candidate_from_record,
    expected_calibration_error,
    label_from_record,
    train_model,
)
from developer_myself.insights.application.history import SessionRecord
from developer_myself.insights.application.model_registry import StoredModel
from developer_myself.insights.application.recommender import (
    ReviewCandidate,
    SpacedRepetitionRule,
    rank,
)
from developer_myself.shared.clock import FakeClock

FAST = TrainingConfig(synthetic_samples=600, epochs=8, hidden=6, patience=3)


def candidate(
    days: float,
    *,
    points: int = 10,
    level: int = 1,
    challenges: int = 3,
    reviews: int = 1,
    rating: int | None = 3,
) -> ReviewCandidate:
    return ReviewCandidate(
        "id",
        "t",
        days,
        points,
        level,
        challenges,
        review_count=reviews,
        days_since_first_session=days + 30,
        last_recall_rating=rating,
        avg_notes_chars=150,
    )


def record(i: int, rating: int, days: float = 10.0) -> SessionRecord:
    t = datetime(2026, 11, 1, tzinfo=UTC)
    return SessionRecord(
        event_id=f"e{i}",
        learner_id="l",
        type="study_session_finished",
        content_id="c",
        content_title="DDD",
        kind="REVIEW",
        started_at=t,
        finished_at=t,
        duration_seconds=1500,
        awarded=True,
        reason=None,
        notes_studied="",
        notes_understood="",
        notes_to_review="",
        level_after="INTERMEDIATE",
        recall_rating=rating,
        level_before="INTERMEDIATE",
        last_contact_days=days,
        points_before=12,
        challenges_solved_before=3,
        review_count_before=2,
        days_since_first_session=40.0,
        avg_notes_chars_before=120.0,
        last_recall_rating_before=3,
    )


# =========================================================================== matemática
class TestMath:
    def test_sigmoid_is_stable_at_extremes(self) -> None:
        assert sigmoid(0) == 0.5
        assert sigmoid(1000) == pytest.approx(1.0)
        assert sigmoid(-1000) == pytest.approx(0.0)

    def test_cross_entropy_punishes_confident_mistakes(self) -> None:
        assert binary_cross_entropy(0.99, 1) < binary_cross_entropy(0.6, 1)
        assert binary_cross_entropy(0.99, 0) > binary_cross_entropy(0.6, 0)

    def test_backprop_matches_numerical_gradient(self) -> None:
        """Gradient check: a derivada analítica (backprop) deve bater com a numérica."""
        model = MLP(n_inputs=3, n_hidden=4, seed=1)
        x, target, eps = [0.2, -0.5, 0.9], 1.0, 1e-6
        analytic = model.gradients(x, target).flat()
        params = model.params()
        for i in range(len(params)):
            plus, minus = params[:], params[:]
            plus[i] += eps
            minus[i] -= eps
            model.set_params(plus)
            loss_plus = binary_cross_entropy(model.predict(x), target)
            model.set_params(minus)
            loss_minus = binary_cross_entropy(model.predict(x), target)
            numeric = (loss_plus - loss_minus) / (2 * eps)
            assert analytic[i] == pytest.approx(numeric, abs=1e-6), f"parâmetro {i}"
        model.set_params(params)

    def test_params_roundtrip(self) -> None:
        model = MLP(n_inputs=3, n_hidden=2, seed=1)
        assert len(model.params()) == model.n_params == 3 * 2 + 2 + 2 + 1
        before = model.predict([1, 2, 3])
        model.set_params(model.params())
        assert model.predict([1, 2, 3]) == before

    def test_sgd_step_descends(self) -> None:
        model = MLP(n_inputs=2, n_hidden=3, seed=2)
        x, t = [0.5, -0.5], 1.0
        before = binary_cross_entropy(model.predict(x), t)
        model.step(model.gradients(x, t), learning_rate=0.5)
        assert binary_cross_entropy(model.predict(x), t) < before


class TestTrainingImprovements:
    def test_adam_minimizes_a_parabola(self) -> None:
        adam, theta = Adam(learning_rate=0.1), [5.0, -3.0]
        for _ in range(300):
            theta = adam.update(theta, [2 * v for v in theta])  # gradiente de x²
        assert theta == pytest.approx([0.0, 0.0], abs=1e-2)

    def test_l2_shrinks_weights(self) -> None:
        xs, ts = [[1.0, 0.0], [0.0, 1.0]], [1.0, 0.0]
        free, decayed = MLP(2, 4, seed=1), MLP(2, 4, seed=1)
        free.fit(xs, ts, epochs=200, learning_rate=0.05, batch_size=2, l2=0.0)
        decayed.fit(xs, ts, epochs=200, learning_rate=0.05, batch_size=2, l2=0.5)
        assert sum(w * w for w in decayed.params()) < sum(w * w for w in free.params())

    def test_l2_does_not_touch_biases(self) -> None:
        model = MLP(n_inputs=1, n_hidden=1, seed=1)
        model.set_params([0.0, 0.0, 0.0, 3.0])  # w1, b1, w2, b2
        grads = model.batch_gradient([[0.0]], [sigmoid(3.0)], [1.0], l2=10.0)
        assert grads[3] == pytest.approx(0.0, abs=1e-9)

    def test_sample_weights_pull_the_prediction(self) -> None:
        xs, ts = [[1.0], [1.0]], [1.0, 0.0]
        model = MLP(n_inputs=1, n_hidden=2, seed=1)
        model.fit(xs, ts, weights=[9.0, 1.0], epochs=300, learning_rate=0.05, batch_size=2, l2=0)
        assert model.predict([1.0]) == pytest.approx(0.9, abs=0.05)

    def test_early_stopping_restores_best_weights(self) -> None:
        train_x, train_t = [[0.0], [1.0]], [0.0, 1.0]
        val_x, val_t = [[0.0], [1.0]], [1.0, 0.0]  # validação contrária: piora ao treinar
        model = MLP(n_inputs=1, n_hidden=2, seed=1)
        result = model.fit(
            train_x, train_t, epochs=100, learning_rate=0.1, batch_size=2,
            validation=(val_x, val_t), patience=3,
        )  # fmt: skip
        assert result.stopped_early
        assert len(result.train_loss) < 100
        assert model.loss(val_x, val_t) == pytest.approx(min(result.val_loss))

    def test_learns_xor_which_a_single_neuron_cannot(self) -> None:
        xs = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]
        ts = [0.0, 1.0, 1.0, 0.0]
        model = MLP(n_inputs=2, n_hidden=4, seed=3)
        result = model.fit(xs, ts, epochs=600, learning_rate=0.05, batch_size=4, l2=0.0)
        assert result.train_loss[-1] < result.train_loss[0]
        assert [round(model.predict(x)) for x in xs] == ts


def test_save_and_load_keep_predictions(tmp_path: Path) -> None:
    model = MLP(n_inputs=4, n_hidden=3, seed=5)
    path = tmp_path / "m.json"
    path.write_text(json.dumps(model.to_dict()))
    loaded = MLP.from_dict(json.loads(path.read_text()))
    assert loaded.predict([0.1, 0.2, 0.3, 0.4]) == model.predict([0.1, 0.2, 0.3, 0.4])


# =========================================================================== features e métricas
class TestFeatures:
    def test_are_normalized(self) -> None:
        values = to_features(
            candidate(days=10_000, points=500, level=2, challenges=50, reviews=999)
        )
        assert len(values) == len(FEATURE_NAMES) == 9
        assert all(0.0 <= v <= 1.0 for v in values)

    def test_unknown_last_rating_is_neutral_and_flagged(self) -> None:
        values = to_features(candidate(days=1, rating=None))
        assert values[6:8] == [0.0, 0.5]
        assert to_features(candidate(days=1, rating=4))[6:8] == [1.0, 1.0]


class TestMetrics:
    def test_brier(self) -> None:
        assert brier([1.0, 0.0], [1.0, 0.0]) == 0.0
        assert brier([0.5, 0.5], [1.0, 0.0]) == 0.25

    def test_calibration_error(self) -> None:
        perfect = [0.25] * 4
        assert expected_calibration_error(perfect, [1.0, 0.0, 0.0, 0.0]) == pytest.approx(0.0)
        assert expected_calibration_error([0.9] * 2, [0.0, 0.0]) == pytest.approx(0.9)

    def test_record_to_training_example(self) -> None:
        r = record(1, rating=1, days=12)
        c = candidate_from_record(r)
        assert c.days_since_last_session == 12
        assert c.level_rank == 1
        assert c.last_recall_rating == 3
        assert label_from_record(r) == 0.0
        assert label_from_record(record(2, rating=2)) == 1.0


# =========================================================================== modelo empacotado
class TestPackagedModel:
    """O `model.json` versionado precisa ter aprendido o bom senso da memória."""

    model = NeuralReviewRecommender.load()

    def test_metadata_documents_training(self) -> None:
        meta = self.model.metadata
        assert meta["trained_on"] == "synthetic"
        assert meta["features"] == 9
        assert float(str(meta["test_log_loss"])) < float(str(meta["baseline_log_loss"]))
        assert float(str(meta["test_calibration_error"])) < 0.1

    def test_forgets_with_time(self) -> None:
        probs = [self.model.recall_probability(candidate(days=d)) for d in (0, 3, 15, 60, 200)]
        assert probs == sorted(probs, reverse=True)
        assert probs[0] > 0.8
        assert probs[-1] < 0.2

    def test_practice_and_mastery_slow_forgetting(self) -> None:
        weak = self.model.recall_probability(candidate(days=20, points=2, level=0, challenges=0))
        strong = self.model.recall_probability(candidate(days=20, points=35, level=2, challenges=6))
        assert strong > weak + 0.2

    def test_last_rating_matters(self) -> None:
        forgot = self.model.recall_probability(candidate(days=10, rating=1))
        easy = self.model.recall_probability(candidate(days=10, rating=4))
        assert easy > forgot + 0.1

    def test_rank_puts_most_forgotten_first(self) -> None:
        fresh, old = candidate(days=1), candidate(days=45)
        ranked = rank(self.model, [fresh, old])
        assert ranked[0].recall_probability < ranked[1].recall_probability


def test_falls_back_to_rule_without_model(tmp_path: Path) -> None:
    recommender = load_best_recommender(tmp_path / "nao-existe.json")
    assert isinstance(recommender, SpacedRepetitionRule)
    assert recommender.recall_probability(candidate(days=0)) == 1.0
    assert recommender.recall_probability(candidate(days=30)) < math.exp(-1)


def test_rejects_model_with_other_features(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"features": ["x"], "weights": {}, "metadata": {}}))
    assert isinstance(load_best_recommender(path), SpacedRepetitionRule)


# =========================================================================== treino com dados reais
def test_training_uses_real_labels_with_more_weight() -> None:
    real = [record(i, rating=1 if i % 4 == 0 else 3) for i in range(20)]
    trained = train_model(real, FAST)
    assert trained.metrics["trained_on"] == "synthetic+real"
    assert trained.metrics["real_samples"] == 20
    assert "real_val_log_loss" in trained.metrics
    assert FAST.real_weight in trained.validation.ws


# =========================================================================== retreino
@pytest.fixture
def store() -> InMemorySessionHistoryStore:
    return InMemorySessionHistoryStore()


async def add_labels(store: InMemorySessionHistoryStore, start: int, n: int) -> None:
    for i in range(start, start + n):
        await store.record(record(i, rating=3))


class TestRetrainJob:
    async def test_first_model_is_promoted(self, store: InMemorySessionHistoryStore) -> None:
        registry = InMemoryModelRegistry()
        job = RetrainJob(store, registry, FakeClock(), FAST, min_new_labels=5)
        report = await job.run_once()
        assert report.status == "promoted"
        active = await registry.active()
        assert active is not None
        assert active.metadata["promoted"] is True

    async def test_skips_without_enough_new_labels(
        self, store: InMemorySessionHistoryStore
    ) -> None:
        registry = InMemoryModelRegistry()
        job = RetrainJob(store, registry, FakeClock(), FAST, min_new_labels=5)
        await job.run_once()
        await add_labels(store, 0, 4)
        assert (await job.run_once()).status == "skipped"
        await add_labels(store, 4, 1)
        assert (await job.run_once()).status in {"promoted", "rejected"}
        assert len(await registry.recent()) == 2

    async def test_worse_challenger_is_kept_but_not_activated(
        self, store: InMemorySessionHistoryStore
    ) -> None:
        registry = InMemoryModelRegistry()
        good = RetrainJob(
            store, registry, FakeClock(), TrainingConfig(synthetic_samples=1500, epochs=20)
        )
        await good.run_once()
        champion = await registry.active()
        bad = RetrainJob(
            store,
            registry,
            FakeClock(),
            TrainingConfig(synthetic_samples=600, epochs=1, hidden=1, learning_rate=1e-5),
        )
        report = await bad.run_once(force=True)
        assert report.status == "rejected"
        assert (await registry.active()) == champion
        assert len(await registry.recent()) == 2

    async def test_champion_with_old_features_always_loses(
        self, store: InMemorySessionHistoryStore
    ) -> None:
        registry = InMemoryModelRegistry()
        old = StoredModel("old", datetime(2026, 1, 1, tzinfo=UTC), True, {"features": ["x"]})
        await registry.publish(old)
        report = await RetrainJob(store, registry, FakeClock(), FAST).run_once(force=True)
        assert report.status == "promoted"


# =========================================================================== recarga sem reiniciar
class TestProvider:
    async def test_reloads_when_a_new_model_is_promoted(self) -> None:
        registry = InMemoryModelRegistry()
        ticks = iter([0.0, 10.0, 100.0])
        provider = RecommenderProvider(SpacedRepetitionRule(), registry, 60, lambda: next(ticks))
        assert (await provider.current()).name == "regra"
        trained = train_model([], FAST)
        await registry.publish(StoredModel("m1", datetime.now(UTC), True, trained.payload()))
        assert (await provider.current()).name == "regra"  # ainda no cache (10 s < 60 s)
        current = await provider.current()  # 100 s: recarrega
        assert isinstance(current, NeuralReviewRecommender)
        assert current.model_id == "m1"

    async def test_broken_model_keeps_the_current_one(self) -> None:
        registry = InMemoryModelRegistry()
        await registry.publish(StoredModel("bad", datetime.now(UTC), True, {"features": ["x"]}))
        provider = RecommenderProvider(SpacedRepetitionRule(), registry, 0)
        assert (await provider.current()).name == "regra"

    async def test_without_registry_uses_fallback(self) -> None:
        assert (await RecommenderProvider(SpacedRepetitionRule()).current()).name == "regra"


def test_dataset_len() -> None:
    data = Dataset()
    data.add(candidate(1), 1.0, 2.0)
    assert len(data) == 1
