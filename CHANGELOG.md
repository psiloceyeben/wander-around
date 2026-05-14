# Changelog

## 0.1.0 — 2026-05-06

Initial public release.

### Engine

- Generic 2D-data → walkable-3D-world engine
- 2D top-down map (`/game`) and first-person 3D world (`/world`) over the same dataset
- CSV and JSONL ingestion
- Four layout algorithms: `ring`, `grid`, `force`, `passthrough`
- Three.js loaded from CDN by default; local override supported
- Mobile path with on-screen D-pad, hamburger menu, welcome panel
- FastAPI app exposed both as a CLI (`wander-around serve`) and as a programmatic `Wander.app()` for embedding

### Examples

- `csv_demo.py` — 50 great books from a static CSV
- `wikipedia_articles.py` — 5,000 Simple-English Wikipedia articles
- `github_repos.py` — top 1,000 GitHub repos by stars
- `personal_bookmarks.py` — your own browser bookmark export

### Docs

- `docs/quickstart.md`
- `docs/customization.md`
- `docs/deployment.md`

### Known limitations

- Datasets above 50K cards: `/api/cards` payload becomes large; viewport-bounded mode is on the roadmap
- Datasets above 500K cards: 3D rendering is one-mesh-per-card; instanced-mesh path is on the roadmap
- Force layout is O(n²) per iteration; not recommended above 5K cards
- No graph-edge rendering yet (force layout reads edges but doesn't draw them)
