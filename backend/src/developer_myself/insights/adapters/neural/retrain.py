"""Retreino automático com champion/challenger (ADR-0012).

1. Junta as revisões com autoavaliação (rótulos reais).
2. Só retreina se chegaram rótulos novos suficientes (ou se `force`).
3. Treina o desafiante numa thread (CPU) para não travar o event loop (ADR-0004).
4. Compara desafiante contra campeão no MESMO conjunto de validação.
5. Guarda o desafiante sempre; ele só vira o ativo se não for pior.

CLI: `python -m developer_myself.insights.adapters.neural.retrain [--force]`
"""

import argparse
import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from developer_myself.insights.adapters.neural.features import FEATURE_NAMES
from developer_myself.insights.adapters.neural.mlp import MLP
from developer_myself.insights.adapters.neural.training import (
    Dataset,
    TrainingConfig,
    evaluate,
    train_model,
)
from developer_myself.insights.application.history import SessionHistoryStore
from developer_myself.insights.application.model_registry import ModelRegistry, StoredModel
from developer_myself.shared.clock import Clock
from developer_myself.shared.logging import log

TOLERANCE = 1e-4


@dataclass(frozen=True, slots=True)
class RetrainReport:
    status: Literal["skipped", "promoted", "rejected"]
    reason: str
    labeled_reviews: int
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrainJob:
    store: SessionHistoryStore
    registry: ModelRegistry
    clock: Clock
    config: TrainingConfig = field(default_factory=TrainingConfig)
    min_new_labels: int = 5

    async def run_once(self, *, force: bool = False) -> RetrainReport:
        labeled = await self.store.labeled_reviews()
        champion = await self.registry.active()
        seen = int(champion.metadata.get("real_samples", 0)) if champion else 0
        new = len(labeled) - seen
        if champion is not None and not force and new < self.min_new_labels:
            return RetrainReport(
                "skipped",
                f"{new} rótulo(s) novo(s); o mínimo para retreinar é {self.min_new_labels}",
                len(labeled),
            )

        trained = await asyncio.to_thread(train_model, labeled, self.config)
        challenger_loss = evaluate(trained.model, trained.validation)
        champion_loss = self._champion_loss(champion, trained.validation)
        promote = champion_loss is None or challenger_loss <= champion_loss + TOLERANCE
        metrics = {
            **trained.metrics,
            "comparison_val_log_loss": round(challenger_loss, 4),
            "champion_val_log_loss": round(champion_loss, 4) if champion_loss else None,
            "champion_id": champion.id if champion else None,
            "promoted": promote,
        }
        payload = trained.payload()
        payload["metadata"] = metrics
        await self.registry.publish(
            StoredModel(str(uuid.uuid7()), self.clock.now(), active=promote, payload=payload)
        )
        if promote:
            reason = "primeiro modelo" if champion is None else "melhor ou igual ao campeão"
        else:
            reason = "pior que o campeão na mesma validação"
        report = RetrainReport("promoted" if promote else "rejected", reason, len(labeled), metrics)
        log.info("model_retrained", status=report.status, reason=reason, real=len(labeled))
        return report

    @staticmethod
    def _champion_loss(champion: StoredModel | None, validation: Dataset) -> float | None:
        if champion is None:
            return None
        if tuple(champion.payload.get("features", ())) != FEATURE_NAMES:
            return None  # campeão com features antigas: o desafiante vence
        return evaluate(MLP.from_dict(champion.payload["weights"]), validation)

    async def run_forever(self, interval_seconds: float, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.run_once()
            except Exception:
                log.exception("retrain_failed")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=interval_seconds)


async def _main(force: bool) -> None:
    from developer_myself.mongo_bootstrap import build_mongo_container  # noqa: PLC0415
    from developer_myself.shared.settings import Settings  # noqa: PLC0415

    container = await build_mongo_container(Settings())
    try:
        report = await container.retrain_job.run_once(force=force)
        print(f"status: {report.status} — {report.reason}")
        print(f"revisões rotuladas: {report.labeled_reviews}")
        for key, value in report.metrics.items():
            print(f"  {key}: {value}")
    finally:
        await container.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retreina a rede com os rótulos reais.")
    parser.add_argument("--force", action="store_true", help="retreina mesmo sem rótulos novos")
    asyncio.run(_main(parser.parse_args().force))
