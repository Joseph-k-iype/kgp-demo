import time


def remaining_timeout(deadline: float | None, maximum: float = 45) -> float:
    if deadline is None:
        return maximum
    remaining = deadline - time.time()
    if remaining <= 0:
        raise TimeoutError("Search exceeded its 90 second limit")
    return min(maximum, remaining)
