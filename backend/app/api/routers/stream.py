import json
import queue
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import current_user
from app.core.security import CurrentUser
from app.services.monitor import subscribe

router = APIRouter(tags=["stream"])


@router.get("/stream")
def stream(
    hire_id: str | None = Query(default=None),
    _: CurrentUser = Depends(current_user),
) -> StreamingResponse:
    events: queue.Queue[dict[str, object]] = queue.Queue()

    def receive(event: dict[str, object]) -> None:
        if hire_id is None or event.get("hireId") == hire_id:
            events.put(event)

    unsubscribe = subscribe(receive)

    def event_stream() -> Iterator[str]:
        try:
            while True:
                event = events.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            unsubscribe()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
