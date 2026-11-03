"""Rate limit simples em memória para o login (credential stuffing, ADR-0009)."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class SlidingWindowLimiter:
    max_hits: int
    window_seconds: float
    _hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and moment - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_hits:
            return False
        hits.append(moment)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
