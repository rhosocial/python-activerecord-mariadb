# concurrency tests

ConcurrencyAware protocol checks and asyncio.create_task scenarios for the shared mysql-connector driver stack, sync and async.

## Key files

- `test_concurrency_protocol.py` — ConcurrencyAware implementation checks (sync)
- `test_concurrency_protocol_async.py` — asyncio.create_task scenarios and driver limits (async)
