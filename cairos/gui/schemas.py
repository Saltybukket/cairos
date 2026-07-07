"""Small dataclasses shared by the optional CAIROS GUI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    display_name: str
    provider: str
    default_model: str
    default_endpoint: str
    default_api_key_env: str
    description: str


@dataclass(frozen=True)
class GuiProfile:
    name: str
    active: bool
    provider: str
    model: str
    endpoint: str
    api_key_env: str
    key_available: bool
    local: bool = False


@dataclass(frozen=True)
class DoctorItem:
    label: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class GuiState:
    version: str
    command_path: str
    config_path: str
    history_path: str
    project_rules_path: str
    platform: str
    shell: str
    active_profile: str
    profiles: list[GuiProfile]
    fallback_enabled: bool
    fallback_order: list[str]
    fallback_persist_switch: bool
    config_schema_version: int
    doctor_items: list[DoctorItem] = field(default_factory=list)


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    level: str = "success"

