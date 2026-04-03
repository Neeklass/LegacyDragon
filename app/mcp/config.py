from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATCH_ROOT = PROJECT_ROOT / "data" / "bronze" / "patches"


def get_patch_root() -> Path:
    raw = os.getenv("LEGACYDRAGON_PATCH_ROOT", str(DEFAULT_PATCH_ROOT))
    return Path(raw).resolve()


def get_default_early_eras() -> tuple[str, ...]:
    """Default eras treated as 'early patches' by the MCP skeleton."""
    return ("alpha", "beta", "season_one")
