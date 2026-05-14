# Wander Around

**Turn any 2D dataset into a walkable 3D world in 60 seconds.**

`wander-around` is a generic engine that takes any tabular data — a CSV, a JSON file, a SQLite query — and renders it as a navigable 3D city you can walk through with WASD on desktop or an on-screen D-pad on mobile. No game-engine knowledge required.

```
pip install wander-around
wander-around serve --csv my_data.csv --layout ring
# → opens http://localhost:8000 — your dataset is now a walkable city
```

## What it does

Given a table with at minimum `(id, label, x, y)` columns and optionally `(category, score, image_url, link)`, the engine:

- **Lays out** every row as a placed entity in a 2D plane using one of several algorithms (ring, grid, force-directed, or pre-computed coordinates from the input)
- **Renders** the layout as both a 2D top-down map (`/game`) and a first-person walkable 3D world (`/world`) where each row is a building
- **Serves** both surfaces through a single FastAPI process; no separate frontend build, no node toolchain, no engine licence
- **Works on mobile** out of the box: D-pad controls, hamburger menu for clutter, welcome panel on first visit

## Why

The dominant interfaces for tabular data are tables and search bars. Both privilege the columns you remember to query. Spatial layout privileges the rows you didn't know existed: walking past 1,000 entities at human pace surfaces what searching cannot.

This project is the engine half of [Wander Around](https://wanderaround.io), where it powers a walkable cartography of ~7M long-tail websites. The model and substrate-language-modelling research from that project lives in a separate repository (`prometheus7/wander-substrate`); this repository is the engine alone, MIT-licensed and meant to be used on any dataset.

## Quickstart

### Install

```bash
pip install wander-around
```

### Serve a CSV

```bash
wander-around serve --csv your_data.csv --layout ring
```

Open http://localhost:8000 — you'll see a 2D ring city (`/game`) and a 3D walkable world (`/world`).

### Required CSV columns

| column | type | required | what it is |
|---|---|---|---|
| `id` | string | yes | unique row identifier |
| `label` | string | yes | display name shown on the building |
| `x`, `y` | float | optional* | pre-computed 2D coordinates |
| `category` | string | optional | clusters rows into colour-coded districts |
| `score` | float | optional | building height / saturation |
| `link` | string | optional | URL opened on click/E-press |
| `image_url` | string | optional | building facade texture |

*If `x`/`y` are omitted, the chosen `--layout` algorithm assigns them.

### Layouts

- `ring` — concentric rings grouped by category; default
- `grid` — uniform grid sorted by score
- `force` — force-directed graph if the data has edges (`--edges edges.csv`)
- `passthrough` — use the `x`,`y` columns as-is

### Examples

```bash
# Walk every Wikipedia article in the Simple-English dump
python examples/wikipedia_articles.py

# Walk every public GitHub repo with > 100 stars
python examples/github_repos.py --token $GITHUB_TOKEN

# Walk your own bookmark export
python examples/personal_bookmarks.py bookmarks.html
```

## Mobile

Open the served URL on your phone. The engine auto-detects touch devices and switches to a sparse mobile UI:

- On-screen D-pad (↑ ← enter → ↓) bottom-right
- Hamburger top-right reveals legend + minimap
- Welcome panel on first visit, dismissible by tap
- Touch-drag anywhere outside the D-pad to look around (3D world)

## Customisation

```python
from wander_around import Wander

w = Wander(
    csv="my_data.csv",
    layout="ring",
    palette={"books": "#a87520", "music": "#3a78c4", "code": "#2c4030"},
    title="My Walkable Library",
    description="A 2D + 3D cartography of my dataset.",
)
w.serve(host="0.0.0.0", port=8000)
```

See [docs/customization.md](docs/customization.md) for the full configuration surface.

## Deployment

`wander-around` is a single FastAPI process; deploy it like any FastAPI app. A reference deployment guide for a single $5/mo VPS with HTTPS via Let's Encrypt is in [docs/deployment.md](docs/deployment.md).

For datasets larger than ~50k entities, see [docs/scaling.md](docs/scaling.md): chunked loading, layout pre-computation, and CDN-backed thumbnail serving.

## License

MIT. See [LICENSE](LICENSE).

## Related

- [wanderaround.io](https://wanderaround.io) — production deployment of this engine over ~7M long-tail websites
- [prometheus7/wander-substrate](https://github.com/Prometheus7/wander-substrate) — the substrate-augmented language model that lives inside the production deployment (separate release)
- [Wander Around preprints](https://wanderaround.io/papers) — research papers from the parent project

## Contributing

PRs welcome. Open an issue first for anything beyond a small fix. The project is intentionally narrow in scope: engine for spatial visualization of tabular data, no machine learning, no engine bundling. Features that fit that scope are very welcome; features that don't (model training, search, recommendation) belong in separate downstream projects.

---

*Built by [psiloceyeben](https://psiloceyeben.com) at the [Prometheus7 Institute](https://prometheus7.com). Inspired by the long-tail web's quiet majority.*
