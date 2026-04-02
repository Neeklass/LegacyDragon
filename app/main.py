from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    patch_count: int
    item_count: int
    patch_ids: list[str]
    item_slugs: list[str]


class PatchDocument(BaseModel):
    patch_id: str
    era: str
    item_change_count: int
    items_changed: list[str]
    source_files: list[str]


class ItemTimelineEntry(BaseModel):
    item_name: str
    item_slug: str
    era: str
    patch_id: str
    matched_keywords: list[str]
    keyword_match_count: int
    source_html: str
    source_patch_dir: str


class ItemDocument(BaseModel):
    item_slug: str
    item_name: str
    change_count: int
    timeline: list[ItemTimelineEntry]


class SearchResponse(BaseModel):
    query: str
    patch_matches: list[str]
    item_matches: list[str]


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_ROOT = PROJECT_ROOT / "data" / "gold" / "items" / "api"
API_ROOT = Path(os.getenv("LEGACYDRAGON_GOLD_API_ROOT", str(DEFAULT_API_ROOT))).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {path.name}") from exc


@lru_cache(maxsize=1)
def get_index() -> IndexResponse:
    payload = _read_json(API_ROOT / "index.json")
    return IndexResponse.model_validate(payload)


app = FastAPI(
    title="LegacyDragon Gold API",
    description="MVP API serving item change data from Gold artifacts.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    status = "ok" if (API_ROOT / "index.json").exists() else "missing_data"
    return {"status": status, "gold_api_root": str(API_ROOT)}


@app.get("/metadata", response_model=IndexResponse)
def metadata() -> IndexResponse:
    return get_index()


@app.get("/patches", response_model=list[str])
def list_patches(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[str]:
    patch_ids = get_index().patch_ids
    return patch_ids[offset : offset + limit]


@app.get("/items", response_model=list[str])
def list_items(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[str]:
    item_slugs = get_index().item_slugs
    return item_slugs[offset : offset + limit]


@app.get("/patches/{patch_id}", response_model=PatchDocument)
def get_patch(patch_id: str) -> PatchDocument:
    payload = _read_json(API_ROOT / "patches" / f"{patch_id}.json")
    return PatchDocument.model_validate(payload)


@app.get("/items/{item_slug}", response_model=ItemDocument)
def get_item(item_slug: str) -> ItemDocument:
    payload = _read_json(API_ROOT / "items" / f"{item_slug}.json")
    return ItemDocument.model_validate(payload)


@app.get("/search", response_model=SearchResponse)
def search(
    query: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=200),
) -> SearchResponse:
    q = query.lower().strip()
    idx = get_index()
    patch_matches = [patch for patch in idx.patch_ids if q in patch.lower()][:limit]
    item_matches = [item for item in idx.item_slugs if q in item.lower()][:limit]
    return SearchResponse(query=query, patch_matches=patch_matches, item_matches=item_matches)
