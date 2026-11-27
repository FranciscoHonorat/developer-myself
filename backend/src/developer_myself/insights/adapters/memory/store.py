from dataclasses import dataclass, field
from datetime import datetime

from developer_myself.insights.application.history import (
    HistoryCursor,
    LearnerHistorySummary,
    SessionRecord,
)


@dataclass(slots=True)
class InMemorySessionHistoryStore:
    _records: dict[str, SessionRecord] = field(default_factory=dict)

    async def record(self, record: SessionRecord) -> bool:
        if record.event_id in self._records:
            return False
        self._records[record.event_id] = record
        return True

    async def list_for(
        self, learner_id: str, limit: int, since: datetime | None = None
    ) -> list[SessionRecord]:
        found = [
            r
            for r in self._records.values()
            if r.learner_id == learner_id and (since is None or r.finished_at >= since)
        ]
        return sorted(found, key=lambda r: r.finished_at, reverse=True)[:limit]

    async def page_for(
        self, learner_id: str, limit: int, after: HistoryCursor | None = None
    ) -> list[SessionRecord]:
        found = [
            r
            for r in self._records.values()
            if r.learner_id == learner_id and (after is None or after.is_after(r))
        ]
        return sorted(found, key=lambda r: (r.finished_at, r.event_id), reverse=True)[:limit]

    async def count_for(self, learner_id: str) -> int:
        return sum(1 for r in self._records.values() if r.learner_id == learner_id)

    async def summaries_for(self, learner_ids: list[str]) -> dict[str, LearnerHistorySummary]:
        wanted = set(learner_ids)
        counts: dict[str, int] = {}
        latest: dict[str, datetime] = {}
        for r in self._records.values():
            if r.learner_id not in wanted:
                continue
            counts[r.learner_id] = counts.get(r.learner_id, 0) + 1
            prev = latest.get(r.learner_id)
            if prev is None or r.finished_at > prev:
                latest[r.learner_id] = r.finished_at
        return {lid: LearnerHistorySummary(counts[lid], latest[lid]) for lid in counts}

    async def delete_for(self, learner_id: str) -> None:
        for key in [k for k, r in self._records.items() if r.learner_id == learner_id]:
            del self._records[key]

    async def labeled_reviews(self, limit: int = 100_000) -> list[SessionRecord]:
        found = [r for r in self._records.values() if r.is_labeled_review]
        return sorted(found, key=lambda r: r.finished_at)[:limit]
