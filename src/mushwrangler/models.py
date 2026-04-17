from __future__ import annotations

from enum import IntEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ColorMode(IntEnum):
    NoColor = 0
    ANSI16 = 1
    XTERM256 = 2
    TrueColor = 3


class Host(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str = ""
    port: int = 0
    tls: bool = False


class ProxySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "NoProxy"
    host_name: str = ""
    port: int = 0
    user: str = ""
    password: str = ""


class FontSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str = ""
    style: str = "Normal"
    size: int = 11


class DisplaySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_text: FontSpec = Field(default_factory=FontSpec)
    output_text: FontSpec = Field(default_factory=FontSpec)
    charset: str = "utf-8"


class DisplayOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_text: Optional[FontSpec] = None
    output_text: Optional[FontSpec] = None
    charset: Optional[str] = None


class TimerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str = ""
    interval_ms: int = 5000
    command_script: str = ""
    enabled: bool = True


class MainWindowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = 80
    y: int = 80
    width: int = 1280
    height: int = 800
    window_state: str = "normal"


class GlobalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display: DisplaySettings = Field(default_factory=DisplaySettings)
    main_window: MainWindowState = Field(default_factory=MainWindowState)


class WindowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = 40
    y: int = 40
    width: int = 900
    height: int = 560


class World(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str = ""
    host: Host = Field(default_factory=Host)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    proxy_id: Optional[UUID] = None
    display: DisplayOverrides = Field(default_factory=DisplayOverrides)
    timers: list[TimerEntry] = Field(default_factory=list)


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    world_id: UUID = Field(default_factory=uuid4)
    name: str = ""
    proxy_id: Optional[UUID] = None
    login: str = ""
    password: str = ""
    login_script: str = ""
    host_override: Optional[Host] = None
    window: Optional[WindowState] = None
    split_input: bool = False
    launch_on_startup: bool = False
    display: DisplayOverrides = Field(default_factory=DisplayOverrides)
    timers: list[TimerEntry] = Field(default_factory=list)
