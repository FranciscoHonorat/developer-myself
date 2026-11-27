"""Rate limit em memória por janela deslizante (ADR-0009).

Serve um único processo (o `uvicorn` do Dockerfile). Com vários workers, cada um teria o
próprio contador; aí o lugar certo é um store compartilhado (Redis) ou o proxy.
"""

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class SlidingWindowLimiter:
    max_hits: int
    window_seconds: float
    # A cada N chamadas, apaga as chaves cujos acertos já saíram da janela (IPs que sumiram).
    sweep_every: int = 1_000
    # Teto de chaves em memória: impede exaustão por flood de IPs/usernames aleatórios.
    max_keys: int = 50_000
    _hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _calls: int = 0

    @property
    def tracked_keys(self) -> int:
        return len(self._hits)

    def hit(self, key: str, now: float | None = None) -> int:
        """Registra um acerto. Devolve 0 se passou, ou quantos segundos esperar se bloqueou."""
        moment = time.monotonic() if now is None else now
        self._calls += 1
        if self._calls % self.sweep_every == 0:
            self._sweep(moment)
        if key not in self._hits and len(self._hits) >= self.max_keys:
            self._sweep(moment)
            while len(self._hits) >= self.max_keys:
                del self._hits[next(iter(self._hits))]
        hits = self._hits[key]
        while hits and moment - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_hits:
            return max(1, math.ceil(hits[0] + self.window_seconds - moment))
        hits.append(moment)
        return 0

    def allow(self, key: str, now: float | None = None) -> bool:
        return self.hit(key, now) == 0

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def _sweep(self, moment: float) -> None:
        idle = [k for k, h in self._hits.items() if not h or moment - h[-1] >= self.window_seconds]
        for key in idle:
            del self._hits[key]
