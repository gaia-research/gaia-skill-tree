## 2024-05-12 - CLI Startup Latency
**Learning:** `importlib.metadata` is a major bottleneck for CLI startup time, causing ~80ms latency on every invocation if imported globally.
**Action:** Always defer imports of heavy stdlib modules like `importlib.metadata` into the specific command functions that need them.
