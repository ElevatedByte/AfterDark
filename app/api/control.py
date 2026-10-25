"""One command service for HTTP and WebSocket transports."""

from pydantic import BaseModel, ConfigDict, Field
from app.state.app_state import EFFECTS, SettingsPatch


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(max_length=64)
    value: str | None = Field(None, max_length=64)
    settings: SettingsPatch | None = None
    person_id: int | None = Field(None, ge=1)
    effects: list[str] | None = Field(None, max_length=len(EFFECTS))
    request_id: str | None = Field(None, max_length=64)


def dispatch(state, command: Command):
    action = command.action
    if action in ("show_start", "show_stop"):
        state.set_show(action == "show_start")
    elif action in ("camera_start", "camera_stop"):
        state.update(camera_requested=action == "camera_start", camera_error=None)
    elif action in ("projector_start", "projector_stop"):
        state.update(
            projector_requested=action == "projector_start", projector_error=None
        )
    elif action == "scene":
        state.set_scene(command.value)
    elif action in ("effect_enable", "effect_disable"):
        state.set_effect(command.value, action == "effect_enable")
    elif action == "trigger":
        state.trigger(command.value)
    elif action == "settings":
        if command.settings is None:
            raise ValueError("settings object required")
        state.settings(command.settings)
    elif action == "person_effects":
        if command.person_id is None:
            raise ValueError("person_id required")
        state.assign_person(command.person_id, command.effects)
    else:
        raise ValueError(f"Unknown action: {action}")
    return state.snapshot()
