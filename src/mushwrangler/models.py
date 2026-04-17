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
    proxy_id: Optional[UUID] = None


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    world_id: UUID = Field(default_factory=uuid4)
    name: str = ""
    proxy_id: Optional[UUID] = None
    login: str = ""
    host_override: Optional[Host] = None
    window: Optional[WindowState] = None
