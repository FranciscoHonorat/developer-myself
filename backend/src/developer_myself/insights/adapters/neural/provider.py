"""Entrega o recomendador ativo e o recarrega do registro sem reiniciar a API."""

import time
from collections.abc import Callable

from developer_myself.insights.adapters.neural.recommender import NeuralReviewRecommender
from developer_myself.insights.application.model_registry import ModelRegistry
from developer_myself.insights.application.recommender import ReviewRecommender
from developer_myself.shared.logging import log


class RecommenderProvider:
    def __init__(
        self,
        fallback: ReviewRecommender,
        registry: ModelRegistry | None = None,
        refresh_seconds: float = 60.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._current = fallback
        self._registry = registry
        self._refresh = refresh_seconds
        self._monotonic = monotonic
        self._checked_at: float | None = None
        self._loaded_id: str | None = None

    async def current(self) -> ReviewRecommender:
        now = self._monotonic()
        stale = self._checked_at is None or now - self._checked_at >= self._refresh
        if self._registry is not None and stale:
            self._checked_at = now
            await self._reload(self._registry)
        return self._current

    async def _reload(self, registry: ModelRegistry) -> None:
        try:
            stored = await registry.active()
            if stored is None or stored.id == self._loaded_id:
                return
            self._current = NeuralReviewRecommender.from_payload(stored.payload, stored.id)
            self._loaded_id = stored.id
            log.info("recommender_reloaded", model_id=stored.id)
        except Exception:
            log.exception("recommender_reload_failed")
