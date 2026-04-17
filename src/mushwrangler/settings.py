from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from mushwrangler.models import Character, Host, World


@dataclass
class SettingsData:
    worlds: dict[UUID, World] = field(default_factory=dict)
    characters: dict[UUID, Character] = field(default_factory=dict)


def seed_demo_settings() -> SettingsData:
    settings = SettingsData()

    world = World(
        name="Convergence MUSH",
        host=Host(address="game.convergencemush.org", port=10000, tls=False),
    )
    settings.worlds[world.id] = world

    char = Character(world_id=world.id, name="Volund")
    settings.characters[char.id] = char

    return settings
