"""Steps da recomendação: o caso de uso real + o modelo treinado versionado."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.conftest import World

from developer_myself.insights.adapters.memory.model_registry import InMemoryModelRegistry
from developer_myself.insights.adapters.neural.provider import RecommenderProvider
from developer_myself.insights.adapters.neural.recommender import (
    NeuralReviewRecommender,
    load_best_recommender,
)
from developer_myself.insights.adapters.neural.retrain import RetrainJob, RetrainReport
from developer_myself.insights.adapters.neural.training import TrainingConfig
from developer_myself.insights.application.recommender import Recommendation, rank
from developer_myself.review_candidates import review_candidates

scenarios("recomendacao.feature")

RECOMMENDER = load_best_recommender()


@when("eu peço uma recomendação de revisão", target_fixture="recommendations")
def when_ask(world: World) -> list[Recommendation]:
    return rank(RECOMMENDER, review_candidates(world.plan(), world.clock.now()))


@then("a recomendação vem da rede neural")
def then_neural() -> None:
    assert RECOMMENDER.name == "rede-neural"


@then(parsers.parse('"{first}" vem antes de "{second}"'))
def then_order(recommendations: list[Recommendation], first: str, second: str) -> None:
    titles = [r.title for r in recommendations]
    assert titles.index(first) < titles.index(second)


@then(
    parsers.re(
        r'a chance estimada de lembrar "(?P<title>[^"]+)" é (?P<cmp>menor|maior) que (?P<pct>\d+)%'
    )
)
def then_probability(recommendations: list[Recommendation], title: str, cmp: str, pct: str) -> None:
    prob = next(r.recall_probability for r in recommendations if r.title == title)
    limit = int(pct) / 100
    assert prob < limit if cmp == "menor" else prob > limit, f"{title}: {prob:.2f}"


@then("não há nada para revisar")
def then_empty(recommendations: list[Recommendation]) -> None:
    assert recommendations == []


# ================================================================== retreino
FAST = TrainingConfig(synthetic_samples=600, epochs=8, hidden=6, patience=3)


@pytest.fixture
def registry() -> InMemoryModelRegistry:
    return InMemoryModelRegistry()


@pytest.fixture
def job(world: World, registry: InMemoryModelRegistry) -> RetrainJob:
    return RetrainJob(world.history, registry, world.clock, FAST, min_new_labels=5)


@given(parsers.parse('que fiz {n:d} revisões avaliadas de "{title}", uma por semana'))
def given_rated_reviews(world: World, n: int, title: str) -> None:
    for i in range(n):
        world.clock.advance(days=7)
        world.session(title, 25, rating=1 if i % 3 == 0 else 3)


@given("que o retreino automático já rodou")
@when("o retreino automático roda", target_fixture="report")
def when_retrain(world: World, job: RetrainJob) -> RetrainReport:
    return world.run(job.run_once())


@then("um novo modelo é ativado")
def then_model_activated(report: RetrainReport) -> None:
    assert report.status == "promoted", report.reason


@then(parsers.parse("ele foi treinado com {n:d} revisões minhas"))
def then_trained_on_mine(world: World, registry: InMemoryModelRegistry, n: int) -> None:
    active = world.run(registry.active())
    assert active is not None
    assert active.metadata["real_samples"] == n
    assert active.metadata["trained_on"] == "synthetic+real"


@then("a recomendação passa a usar esse modelo")
def then_provider_uses_it(world: World, registry: InMemoryModelRegistry) -> None:
    provider = RecommenderProvider(RECOMMENDER, registry, refresh_seconds=0)
    current = world.run(provider.current())
    active = world.run(registry.active())
    assert isinstance(current, NeuralReviewRecommender)
    assert active is not None
    assert current.model_id == active.id


@then("o retreino é adiado por falta de rótulos novos")
def then_skipped(report: RetrainReport) -> None:
    assert report.status == "skipped"
    assert "2 rótulo(s) novo(s)" in report.reason
