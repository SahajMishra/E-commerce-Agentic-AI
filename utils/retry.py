import asyncio
import random
from typing import Any, Awaitable, Callable, Iterable, Optional, Type


class RetryError(Exception):
    pass


async def retry_async(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    retries: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    retriable_exceptions: Optional[Iterable[Type[BaseException]]] = None,
    **kwargs: Any,
) -> Any:
    exceptions = tuple(retriable_exceptions or (Exception,))
    last_error: Optional[BaseException] = None

    for attempt in range(1, retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as exc:
            last_error = exc
            if attempt == retries:
                break
            wait = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, wait * 0.2)
            await asyncio.sleep(wait + jitter)

    raise RetryError(f"Operation failed after {retries} retries: {last_error}") from last_error
