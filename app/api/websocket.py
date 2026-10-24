import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from app.api.control import Command, dispatch

router = APIRouter()


@router.websocket("/ws")
async def controller(websocket: WebSocket):
    # Local controller: reject browser requests originating at another website.
    origin = websocket.headers.get("origin")
    if origin and origin not in (
        f"http://{websocket.headers.get('host')}",
        f"https://{websocket.headers.get('host')}",
    ):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    state = websocket.app.state.show
    send_lock = asyncio.Lock()

    async def send(payload):
        async with send_lock:
            await websocket.send_json(payload)

    async def statuses():
        while True:
            await send({"type": "status", "data": state.snapshot()})
            await asyncio.sleep(0.2)

    task = asyncio.create_task(statuses())
    try:
        while True:
            command = None
            try:
                raw = await websocket.receive_text()
                if len(raw) > 8192:
                    await websocket.close(code=1009)
                    break
                command = Command.model_validate_json(raw)
                snapshot = dispatch(state, command)
                await send(
                    {"type": "ack", "request_id": command.request_id, "data": snapshot}
                )
            except (ValueError, ValidationError) as exc:
                await send(
                    {
                        "type": "error",
                        "request_id": command.request_id if command else None,
                        "message": str(exc),
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
            pass
