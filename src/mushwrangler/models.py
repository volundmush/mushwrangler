from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Host:
    address: str = ""
    port: int = 0
    tls: bool = False


@dataclass
class World:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    host: Host = field(default_factory=Host)
    proxy_id: Optional[UUID] = None


@dataclass
class Character:
    id: UUID = field(default_factory=uuid4)
    world_id: UUID = field(default_factory=uuid4)
    name: str = ""
    proxy_id: Optional[UUID] = None
