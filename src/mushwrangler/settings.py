from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import QStandardPaths

from mushwrangler.models import Character, World


class SettingsData:
    def __init__(self) -> None:
        self.worlds: dict[UUID, World] = {}
        self.characters: dict[UUID, Character] = {}


def app_data_dir() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not base:
        base = str(Path.home() / ".mushwrangler")
    return Path(base)


def _ensure_layout(root: Path) -> tuple[Path, Path]:
    worlds_dir = root / "worlds"
    chars_dir = root / "characters"
    worlds_dir.mkdir(parents=True, exist_ok=True)
    chars_dir.mkdir(parents=True, exist_ok=True)
    return worlds_dir, chars_dir


def save_settings(settings: SettingsData, root: Path | None = None) -> None:
    root_path = root or app_data_dir()
    worlds_dir, chars_dir = _ensure_layout(root_path)

    world_ids = {world.id for world in settings.worlds.values()}
    char_ids = {character.id for character in settings.characters.values()}

    for path in worlds_dir.glob("*.json"):
        try:
            uid = UUID(path.stem)
        except ValueError:
            continue
        if uid not in world_ids:
            path.unlink(missing_ok=True)

    for path in chars_dir.glob("*.json"):
        try:
            uid = UUID(path.stem)
        except ValueError:
            continue
        if uid not in char_ids:
            path.unlink(missing_ok=True)

    for world in settings.worlds.values():
        path = worlds_dir / f"{world.id}.json"
        path.write_text(
            world.model_dump_json(indent=2),
            encoding="utf-8",
        )

    for character in settings.characters.values():
        path = chars_dir / f"{character.id}.json"
        path.write_text(
            character.model_dump_json(indent=2),
            encoding="utf-8",
        )


def load_settings(root: Path | None = None) -> SettingsData:
    root_path = root or app_data_dir()
    worlds_dir, chars_dir = _ensure_layout(root_path)

    settings = SettingsData()

    for path in sorted(worlds_dir.glob("*.json")):
        try:
            world = World.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        settings.worlds[world.id] = world

    for path in sorted(chars_dir.glob("*.json")):
        try:
            character = Character.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue

        if character.world_id not in settings.worlds:
            continue
        settings.characters[character.id] = character

    return settings


def save_world(world: World, root: Path | None = None) -> None:
    root_path = root or app_data_dir()
    worlds_dir, _ = _ensure_layout(root_path)
    path = worlds_dir / f"{world.id}.json"
    path.write_text(world.model_dump_json(indent=2), encoding="utf-8")


def save_character(character: Character, root: Path | None = None) -> None:
    root_path = root or app_data_dir()
    _, chars_dir = _ensure_layout(root_path)
    path = chars_dir / f"{character.id}.json"
    path.write_text(character.model_dump_json(indent=2), encoding="utf-8")


def delete_world(world_id: UUID, root: Path | None = None) -> None:
    root_path = root or app_data_dir()
    worlds_dir, _ = _ensure_layout(root_path)
    (worlds_dir / f"{world_id}.json").unlink(missing_ok=True)


def delete_character(character_id: UUID, root: Path | None = None) -> None:
    root_path = root or app_data_dir()
    _, chars_dir = _ensure_layout(root_path)
    (chars_dir / f"{character_id}.json").unlink(missing_ok=True)
