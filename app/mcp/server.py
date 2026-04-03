from __future__ import annotations

from .config import get_patch_root
from .data_access import list_early_patch_ids, list_eras, list_patch_ids, patch_path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - import guard for local setup
    raise RuntimeError(
        "The 'mcp' package is required for the MCP server. Install deps with: uv sync"
    ) from exc


mcp = FastMCP("LegacyDragon Early Patch MCP")


@mcp.tool()
def health() -> dict[str, str]:
    """Simple server health and data-root check."""
    root = get_patch_root()
    return {"status": "ok" if root.exists() else "missing_data", "patch_root": str(root)}


@mcp.tool()
def get_eras() -> list[str]:
    """List all era folders available under the patch dataset."""
    return list_eras()


@mcp.tool()
def get_patch_ids(era: str) -> list[str]:
    """List patch IDs for a specific era, for example 'beta' or 'season_one'."""
    return list_patch_ids(era)


@mcp.tool()
def get_early_patch_index() -> dict[str, list[str]]:
    """Return patch IDs grouped by early eras (alpha/beta/season_one)."""
    return list_early_patch_ids()


@mcp.tool()
def describe_patch_location(era: str, patch_id: str) -> dict[str, str | bool]:
    """Return filesystem location and existence check for one patch snapshot."""
    path = patch_path(era, patch_id)
    return {"exists": path.exists(), "path": str(path), "era": era, "patch_id": patch_id}
