import asyncio
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from app.api.control import Command, dispatch
from app.state.app_state import EFFECTS, SettingsPatch

router = APIRouter(prefix="/api")


def execute(request, **kwargs):
    try:
        return dispatch(request.app.state.show, Command(**kwargs))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/status")
def status(request: Request):
    return request.app.state.show.snapshot()


@router.post("/camera/{action}")
def camera(action: str, request: Request):
    if action not in ("start", "stop"):
        raise HTTPException(404, "Unknown camera action")
    return execute(request, action=f"camera_{action}")


@router.post("/projector/{action}")
def projector(action: str, request: Request):
    if action not in ("start", "stop"):
        raise HTTPException(404, "Unknown projector action")
    return execute(request, action=f"projector_{action}")


@router.post("/scene/{scene_name}")
def scene(scene_name: str, request: Request):
    return execute(request, action="scene", value=scene_name)


@router.post("/effects/{effect_name}/{action}")
def effect(effect_name: str, action: str, request: Request):
    if action not in ("enable", "disable"):
        raise HTTPException(404, "Unknown effect action")
    return execute(request, action=f"effect_{action}", value=effect_name)


@router.post("/trigger/{trigger_name}")
def trigger(trigger_name: str, request: Request):
    return execute(request, action="trigger", value=trigger_name)


@router.post("/settings")
def settings(patch: SettingsPatch, request: Request):
    return execute(request, action="settings", settings=patch)


class PersonEffects(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effects: list[str] | None = Field(None, max_length=len(EFFECTS))


@router.post("/people/{person_id}/effects")
def person_effects(person_id: int, payload: PersonEffects, request: Request):
    return execute(
        request, action="person_effects", person_id=person_id, effects=payload.effects
    )


@router.get("/preview.jpg")
def preview(request: Request):
    jpeg = request.app.state.runtime.preview()
    if not jpeg:
        return Response(status_code=204)
    return Response(
        jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
    )


@router.get("/output.jpg")
def output_snapshot(request: Request):
    jpeg = request.app.state.runtime.output_snapshot()
    if not jpeg:
        return Response(status_code=204)
    return Response(
        jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
    )


@router.get("/preview.mjpg")
async def preview_stream(request: Request):
    async def frames():
        while (
            not request.app.state.shutting_down and not await request.is_disconnected()
        ):
            jpeg = request.app.state.runtime.preview()
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            await asyncio.sleep(0.12)

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )
