from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from bs4 import BeautifulSoup, Comment
from tqdm import tqdm


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT_DIR / "data" / "source"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "cleaned_patches.json"


MONTH_LOOKUP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


SECTION_SKIP_KEYWORDS = {
    "faq",
    "guide",
    "overview",
    "how to",
    "boards",
    "community",
    "comments",
    "discussion",
    "forum",
}

ITEM_SECTION_KEYWORDS = {
    "items",
    "item changes",
    "item updates",
}

BALANCE_SECTION_KEYWORDS = {
    "balance",
    "runes",
    "masteries",
    "summoner spells",
    "systems",
    "general",
    "gameplay",
}


@dataclass
class PatchData:
    patch: str | None
    release_date: str | None
    champion_changes: list[dict]
    item_changes: list[dict]
    balance_updates: list[dict]
    source_path: str

    def to_dict(self) -> dict:
        return {
            "patch": self.patch,
            "release_date": self.release_date,
            "champion_changes": self.champion_changes,
            "item_changes": self.item_changes,
            "balance_updates": self.balance_updates,
            "source_path": self.source_path,
        }


def iter_html_files(source_dir: Path) -> Iterable[Path]:
    return sorted(source_dir.rglob("*.html"))


def clean_soup(soup: BeautifulSoup) -> None:
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in soup.find_all(["script", "style", "iframe", "noscript", "svg"]):
        tag.decompose()

    for tag in soup.find_all(True):
        classes = tag.get("class") or []
        class_text = " ".join(classes).lower()
        if "ad" in classes or " ad " in f" {class_text} ":
            tag.decompose()
            continue
        if "post-content" in classes:
            tag.decompose()
            continue


def find_content_root(soup: BeautifulSoup) -> BeautifulSoup:
    candidates = []
    for tag in soup.find_all(True, class_=True):
        classes = tag.get("class") or []
        class_text = " ".join(classes).lower()
        if any(key in class_text for key in ["post-message", "post_message", "post-content"]):
            candidates.append(tag)
    if candidates:
        return candidates[0]
    return soup.body or soup


def parse_patch_number(text: str, path: Path) -> str | None:
    version_match = re.search(r"\b(v?\d+\.\d+\.\d+\.\d+[a-z]?)\b", text, re.IGNORECASE)
    if version_match:
        return version_match.group(1).lstrip("v")

    path_match = re.search(r"\b(\d+\.\d+\.\d+\.\d+[a-z]?)\b", str(path))
    if path_match:
        return path_match.group(1)

    minor_match = re.search(r"\b(v?\d+\.\d+)\b", text, re.IGNORECASE)
    if minor_match:
        return minor_match.group(1).lstrip("v")

    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", str(path))
    if date_match:
        return date_match.group(1)

    return None


def parse_release_date(soup: BeautifulSoup, text: str, path: Path) -> str | None:
    body = soup.find("body")
    if body:
        class_text = " ".join(body.get("class") or [])
        date_match = re.search(r"date-(\d{8})", class_text)
        if date_match:
            value = date_match.group(1)
            return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"

    path_date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", str(path))
    if path_date:
        return path_date.group(1)

    numeric_date = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text)
    if numeric_date:
        month, day, year = numeric_date.groups()
        year = year if len(year) == 4 else f"20{year}"
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    month_date = re.search(
        r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(\d{4})\b",
        text,
    )
    if month_date:
        month_name, day, year = month_date.groups()
        month = MONTH_LOOKUP.get(month_name.lower())
        if month:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"

    return None


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def classify_change(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["buff", "increased", "improved", "+"]):
        if any(token in lowered for token in ["reduced", "decreased", "nerf", "-"]):
            return "adjust"
        return "buff"
    if any(token in lowered for token in ["nerf", "reduced", "decreased", "lowered", "-"]):
        return "nerf"
    return "adjust"


def is_section_skippable(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in SECTION_SKIP_KEYWORDS)


def extract_list_items(ul_tag) -> list[str]:
    items = []
    for li in ul_tag.find_all("li", recursive=False):
        text = normalize_text(li.get_text(" "))
        if text:
            items.append(text)
    return items


def extract_champion_changes(content: BeautifulSoup) -> list[dict]:
    changes = []
    for bold in content.find_all("b"):
        title = normalize_text(bold.get_text(" "))
        if not title:
            continue
        if title.lower() in ITEM_SECTION_KEYWORDS or title.lower() in BALANCE_SECTION_KEYWORDS:
            continue
        if is_section_skippable(title):
            continue

        next_ul = bold.find_next_sibling("ul")
        if not next_ul:
            continue

        for change_text in extract_list_items(next_ul):
            changes.append(
                {
                    "champion": title,
                    "change": change_text,
                    "type": classify_change(change_text),
                }
            )
    return changes


def extract_item_changes(content: BeautifulSoup) -> list[dict]:
    changes = []

    def get_item_name(li_tag) -> str | None:
        parts = []
        for child in li_tag.contents:
            if getattr(child, "name", None) == "ul":
                break
            if isinstance(child, str):
                parts.append(child)
            elif getattr(child, "get_text", None):
                parts.append(child.get_text(" "))
        name = normalize_text(" ".join(parts))
        return name or None

    for bold in content.find_all("b"):
        title = normalize_text(bold.get_text(" "))
        if title.lower() not in ITEM_SECTION_KEYWORDS:
            continue
        next_ul = bold.find_next_sibling("ul")
        if not next_ul:
            continue

        for li in next_ul.find_all("li", recursive=False):
            nested = li.find("ul")
            if nested:
                item_name = get_item_name(li)
                for change_text in extract_list_items(nested):
                    changes.append(
                        {
                            "item": item_name,
                            "change": change_text,
                            "type": classify_change(change_text),
                        }
                    )
            else:
                text = normalize_text(li.get_text(" "))
                if text:
                    changes.append(
                        {
                            "item": None,
                            "change": text,
                            "type": classify_change(text),
                        }
                    )

    for table in content.find_all(
        "table",
        class_=lambda value: value and "champion-changes" in " ".join(value).lower(),
    ):
        for row in table.find_all("tr"):
            cells = [normalize_text(cell.get_text(" ")) for cell in row.find_all(["td", "th"])]
            if len(cells) >= 2:
                changes.append(
                    {
                        "item": cells[0],
                        "change": " ".join(cells[1:]),
                        "type": classify_change(" ".join(cells[1:])),
                    }
                )

    return changes


def extract_balance_updates(content: BeautifulSoup) -> list[dict]:
    updates = []

    for bold in content.find_all("b"):
        title = normalize_text(bold.get_text(" "))
        if not title:
            continue
        lowered = title.lower()
        if lowered in ITEM_SECTION_KEYWORDS:
            continue
        if lowered in BALANCE_SECTION_KEYWORDS or "rune" in lowered or "mastery" in lowered:
            next_ul = bold.find_next_sibling("ul")
            if not next_ul:
                continue
            for change_text in extract_list_items(next_ul):
                updates.append({"section": title, "change": change_text})

    for heading in content.find_all(["h2", "h3", "h4"]):
        title = normalize_text(heading.get_text(" "))
        if not title:
            continue
        lowered = title.lower()
        if is_section_skippable(title) or lowered in ITEM_SECTION_KEYWORDS:
            continue
        if any(keyword in lowered for keyword in BALANCE_SECTION_KEYWORDS):
            next_ul = heading.find_next_sibling("ul")
            if not next_ul:
                continue
            for change_text in extract_list_items(next_ul):
                updates.append({"section": title, "change": change_text})

    return updates


def parse_patch_file(path: Path) -> PatchData | None:
    content = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(content, "lxml")
    clean_soup(soup)

    text = soup.get_text(" ")
    patch = parse_patch_number(text, path)
    release_date = parse_release_date(soup, text, path)

    content_root = find_content_root(soup)

    champion_changes = extract_champion_changes(content_root)
    item_changes = extract_item_changes(content_root)
    balance_updates = extract_balance_updates(content_root)

    if not any([champion_changes, item_changes, balance_updates]):
        return None

    return PatchData(
        patch=patch,
        release_date=release_date,
        champion_changes=champion_changes,
        item_changes=item_changes,
        balance_updates=balance_updates,
        source_path=str(path.relative_to(ROOT_DIR)),
    )


def build_dataframe(patches: list[PatchData]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "patch": patch.patch,
                "release_date": patch.release_date,
                "champion_change_count": len(patch.champion_changes),
                "item_change_count": len(patch.item_changes),
                "balance_update_count": len(patch.balance_updates),
                "source_path": patch.source_path,
            }
            for patch in patches
        ]
    )


def run(source_dir: Path, output_path: Path) -> tuple[list[dict], pd.DataFrame]:
    patches: list[PatchData] = []
    for path in tqdm(iter_html_files(source_dir), desc="Parsing HTML files"):
        patch = parse_patch_file(path)
        if patch:
            patches.append(patch)

    patch_dicts = [patch.to_dict() for patch in patches]
    output_path.write_text(json.dumps(patch_dicts, indent=2), encoding="utf-8")

    dataframe = build_dataframe(patches)
    return patch_dicts, dataframe


def main() -> None:
    patch_dicts, dataframe = run(DEFAULT_SOURCE_DIR, DEFAULT_OUTPUT_PATH)

    print(f"Parsed {len(patch_dicts)} patches")
    print(f"Saved JSON to {DEFAULT_OUTPUT_PATH}")
    print(dataframe.head(10))


if __name__ == "__main__":
    main()
