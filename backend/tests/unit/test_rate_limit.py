"""Janela deslizante do rate limit (ADR-0009): quanto falta esperar e limpeza de memória."""

from developer_myself.shared.adapters.rate_limit import SlidingWindowLimiter


def test_allows_up_to_max_hits_inside_the_window() -> None:
    limiter = SlidingWindowLimiter(max_hits=2, window_seconds=60)
    assert limiter.allow("k", now=0)
    assert limiter.allow("k", now=1)
    assert not limiter.allow("k", now=2)


def test_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter(max_hits=1, window_seconds=60)
    assert limiter.allow("a", now=0)
    assert limiter.allow("b", now=0)


def test_hit_returns_seconds_until_the_oldest_hit_leaves_the_window() -> None:
    limiter = SlidingWindowLimiter(max_hits=2, window_seconds=60)
    assert limiter.hit("k", now=0) == 0
    assert limiter.hit("k", now=10) == 0
    assert limiter.hit("k", now=15) == 45
    # Bloqueado não conta como acerto: o 1º acerto sai da janela em t=60.
    assert limiter.hit("k", now=61) == 0


def test_reset_forgets_the_key() -> None:
    limiter = SlidingWindowLimiter(max_hits=1, window_seconds=60)
    limiter.allow("k", now=0)
    limiter.reset("k")
    assert limiter.allow("k", now=1)


def test_idle_keys_are_swept_so_memory_does_not_grow_forever() -> None:
    limiter = SlidingWindowLimiter(max_hits=5, window_seconds=60, sweep_every=3)
    limiter.hit("ip-1", now=0)
    limiter.hit("ip-2", now=0)
    assert limiter.tracked_keys == 2
    limiter.hit("ip-3", now=120)  # 3ª chamada: varre quem já saiu da janela
    assert limiter.tracked_keys == 1
