import threading

from hedge_fund_lab import live_strategies


def test_slow_cache_producer_does_not_hold_shared_lock():
    live_strategies.reset_cache()
    started = threading.Event()
    release = threading.Event()

    def producer():
        started.set()
        assert release.wait(timeout=2)
        return {"ok": True}

    worker = threading.Thread(
        target=lambda: live_strategies._cached("signals", producer),
        daemon=True,
    )
    worker.start()
    assert started.wait(timeout=1)

    acquired = live_strategies._CACHE_LOCK.acquire(timeout=0.2)
    try:
        assert acquired, "network I/O must not hold the shared cache lock"
    finally:
        if acquired:
            live_strategies._CACHE_LOCK.release()
        release.set()
        worker.join(timeout=2)

    assert not worker.is_alive()
    assert live_strategies._CACHE["signals"] == {"ok": True}
