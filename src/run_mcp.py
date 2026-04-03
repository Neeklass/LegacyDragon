from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LegacyDragon MCP server.")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio"],
        help="MCP transport (base skeleton currently supports stdio).",
    )
    return parser.parse_args()


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    args = parse_args()

    from app.mcp.server import mcp

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
