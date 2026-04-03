from __future__ import annotations

from pathlib import Path

from .config import get_default_early_eras, get_patch_root


def list_eras() -> list[str]:
    root = get_patch_root()
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def list_patch_ids(era: str) -> list[str]:
    root = get_patch_root() / era
    if not root.exists() or not root.is_dir():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def list_early_patch_ids() -> dict[str, list[str]]:
    return {era: list_patch_ids(era) for era in get_default_early_eras()}


def patch_path(era: str, patch_id: str) -> Path:
    return get_patch_root() / era / patch_id
