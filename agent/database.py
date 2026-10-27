import logging
import os

import asyncpg

logger = logging.getLogger("sarjy.database")

# Fail fast instead of asyncpg's 60 s default: a voice turn can't wait that long.
TIMEOUT_S = 5
# Neon's IPv6 addresses sometimes swallow a connection attempt (2 in 12 in a local test, IPv4
# never), and asyncio waits on one address at a time, so a stalled attempt is retried.
CONNECT_ATTEMPTS = 3
# Neon closes idle connections, so drop ours before they go stale.
MAX_IDLE_S = 60

_pool: asyncpg.Pool | None = None


async def pool() -> asyncpg.Pool:
    """The process's shared connection pool, created on first use."""
    global _pool
    if _pool is None:
        _pool = await _create_pool()
    return _pool


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _create_pool() -> asyncpg.Pool:
    for attempt in range(1, CONNECT_ATTEMPTS):
        try:
            return await _connect()
        except TimeoutError:
            logger.warning("database connection timed out (attempt %d), retrying", attempt)
    return await _connect()


async def _connect() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=5,
        timeout=TIMEOUT_S,
        command_timeout=TIMEOUT_S,
        max_inactive_connection_lifetime=MAX_IDLE_S,
    )
