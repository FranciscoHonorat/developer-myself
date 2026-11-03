from dataclasses import dataclass, field
from datetime import datetime

from developer_myself.insights.application.history import SessionRecord


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

    async def delete_for(self, learner_id: str) -> None:
        for key in [k for k, r in self._records.items() if r.learner_id == learner_id]:
            del self._records[key]

    async def labeled_reviews(self, limit: int = 100_000) -> list[SessionRecord]:
        found = [r for r in self._records.values() if r.is_labeled_review]
        return sorted(found, key=lambda r: r.finished_at)[:limit]
