"""Live check of every configured provider/model: JSON-schema support, latency, and streaming.

Usage: .venv/bin/python -m scripts.smoke_llm
"""

import asyncio
import logging
import time

from pydantic import BaseModel

from app.config import Settings, build_targets
from app.llm.client import LLMClient, LLMUnavailable


class Ping(BaseModel):
    ok: bool
    word: str


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    targets = build_targets(Settings())
    for t in targets["analysis"]:
        client = LLMClient({"analysis": [t], "writer": [t]}, timeout_s=60)
        started = time.perf_counter()
        try:
            r = await client.structured("analysis", "Reply in JSON.", 'Return {"ok": true, "word": "namaste"}', Ping)
            print(f"{t.label:45} OK   {r.value.word!r:12} {time.perf_counter() - started:5.1f}s")
        except LLMUnavailable:
            print(f"{t.label:45} FAIL {time.perf_counter() - started:5.1f}s")
    if targets["writer"]:
        client = LLMClient(targets, timeout_s=60)
        stream = await client.open_stream("writer", "Be brief.", "Count from one to five in words.")
        text = "".join([chunk async for chunk in stream])
        print(f"stream via {stream.model}: {text[:60]!r}")


if __name__ == "__main__":
    asyncio.run(main())
