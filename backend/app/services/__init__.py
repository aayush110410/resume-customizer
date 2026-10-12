import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.llm.client import LLMUnavailable

log = logging.getLogger("services")


@dataclass
class ServerEvent:
    event: str
    data: dict


def stage(stage_id: str, status: str) -> ServerEvent:
    return ServerEvent("stage", {"id": stage_id, "status": status})


async def as_sse(events: AsyncIterator[ServerEvent]) -> AsyncIterator[dict]:
    """Serialize service events for sse-starlette; failures mid-stream become a final `error` event."""
    try:
        async for e in events:
            yield {"event": e.event, "data": json.dumps(e.data, ensure_ascii=False)}
    except LLMUnavailable:
        body = {"code": "LLM_UNAVAILABLE", "message": "All AI providers are busy right now.", "retryable": True}
        yield {"event": "error", "data": json.dumps(body)}
    except Exception:
        log.exception("stream failed")
        body = {"code": "INTERNAL", "message": "Something went wrong.", "retryable": True}
        yield {"event": "error", "data": json.dumps(body)}
