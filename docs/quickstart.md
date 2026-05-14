# Quickstart

## Install

```bash
pip install wander-around
```

## Walk a CSV

The minimum CSV needs `id` and `label`:

```csv
id,label
a,Apple
b,Banana
c,Cherry
```

```bash
wander-around serve --csv fruits.csv
# → http://localhost:8000
```

The default layout is `ring` (concentric rings grouped by category). Without categories, all rows land in one ring.

## Add categories and scores

```csv
id,label,category,score
a,Apple,fruit,5
b,Banana,fruit,4
c,Carrot,vegetable,3
d,Dill,herb,2
```

Each category becomes a colored district; `score` controls building height.

## Add links

```csv
id,label,category,link
a,Apple,fruit,https://en.wikipedia.org/wiki/Apple
```

When the visitor presses E (or taps "enter") next to a building, the link opens.

## Pre-computed coordinates

If you've already laid out your data (e.g. UMAP, t-SNE, principal components), include `x` and `y` columns and pass `--layout passthrough`:

```bash
wander-around serve --csv data.csv --layout passthrough
```

## Programmatic use

```python
from wander_around import Wander, Card

cards = [
    Card(id="1", label="One", category="numbers"),
    Card(id="2", label="Two", category="numbers"),
    Card(id="a", label="A", category="letters"),
]
w = Wander(cards=cards, layout="ring")
w.serve()
```

## What you see

- `/`  — landing page with two buttons (3D / 2D)
- `/world` — first-person walkable 3D world; WASD to walk, mouse to look, E to open
- `/game` — top-down 2D map; same controls
- On mobile: D-pad bottom-right, hamburger top-right for additional controls

## Common shapes of "this didn't work"

| symptom | likely cause | fix |
|---|---|---|
| empty world | every row missing `id` AND `label` | pick at least one |
| all buildings in a heap | every row in one category | add category column or use `--layout grid` |
| layout crash with passthrough | row missing `x` or `y` | use `ring` instead, or fill the missing coords |
| "Three.js failed to load" | offline / firewalled | drop `three.module.js` and `PointerLockControls.js` into `wander_around/static/` (the server prefers local copies) |
