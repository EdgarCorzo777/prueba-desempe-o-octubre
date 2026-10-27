from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse
from api.app.auth.dependencies import require_role
from api.app.services.sse_manager import earthquake_event_generator

router = APIRouter(prefix="/api/stream", tags=["Realtime Stream"])

@router.get("")
async def sse_event_stream(user: dict = Depends(require_role("viewer"))):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Emits real-time seismic events without full page reload.
    Supports auto-reconnection and client heartbeat.
    """
    return StreamingResponse(
        earthquake_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
