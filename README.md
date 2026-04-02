# LegacyDragon

patch 1.0.0.151 is the official end of season two but isnt in the old data because this is the oldest info I get from riot cdn
(at least to my current understanding)

## Local FastAPI MVP

FastAPI is still state-of-the-art for Python APIs in 2026, especially for fast MVP delivery,
automatic OpenAPI docs, and clear typing.

This repo includes a local MVP API that serves the already-materialized Gold JSON files from:

- data/gold/items/api/index.json
- data/gold/items/api/patches/*.json
- data/gold/items/api/items/*.json

### Start locally

1. Install dependencies (if needed):

	 uv sync

2. Start API server:

	 uv run python src/run_api.py --reload

3. Open docs:

	 http://127.0.0.1:8000/docs

### Available endpoints

- GET /health
	- Quick runtime and data-path check.

- GET /metadata
	- Returns index counts plus all patch IDs and item slugs.

- GET /patches?limit=50&offset=0
	- Paginated patch ID list.

- GET /items?limit=50&offset=0
	- Paginated item slug list.

- GET /patches/{patch_id}
	- Returns one patch document.

- GET /items/{item_slug}
	- Returns one item timeline document.

- GET /search?query=trinity&limit=20
	- Simple substring search across patch IDs and item slugs.

### Optional custom data path

If you want to point to a different Gold API folder:

LEGACYDRAGON_GOLD_API_ROOT=/some/path/to/api uv run python src/run_api.py