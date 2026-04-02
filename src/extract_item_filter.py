from __future__ import annotations

import argparse
import html
from pathlib import Path

from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT_DIR / "data" / "source" / "items_raw.html"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "filter-item.yaml"


def yaml_single_quote(value: str) -> str:
    return value.replace("'", "''")


def parse_item_keywords(input_path: Path) -> dict[str, list[str]]:
    soup = BeautifulSoup(input_path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    result: dict[str, list[str]] = {}

    for tag in soup.find_all(attrs={"data-item": True, "data-search": True}):
        item_name = html.unescape(tag.get("data-item", "")).strip()
        search_value = html.unescape(tag.get("data-search", "")).strip()

        if not item_name:
            continue

        keywords: list[str] = []
        for token in search_value.split(","):
            keyword = token.strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)

        if item_name not in keywords:
            keywords.insert(0, item_name)

        if item_name not in result:
            result[item_name] = []

        for keyword in keywords:
            if keyword not in result[item_name]:
                result[item_name].append(keyword)

    return result


def write_yaml(items: dict[str, list[str]], output_path: Path) -> None:
    lines = ["items:"]

    for item_name in sorted(items):
        escaped_name = yaml_single_quote(item_name)
        keyword_values = ", ".join(
            f"'{yaml_single_quote(keyword)}'" for keyword in items[item_name]
        )
        lines.append(f"  - name: '{escaped_name}'")
        lines.append(f"    keywords: [{keyword_values}]")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract item names and search keywords into a filter YAML file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the HTML file containing item data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for the generated YAML file.",
    )
    args = parser.parse_args()

    items = parse_item_keywords(args.input)
    write_yaml(items, args.output)

    print(f"Extracted {len(items)} items")
    print(f"Saved item filter to {args.output}")


if __name__ == "__main__":
    main()
