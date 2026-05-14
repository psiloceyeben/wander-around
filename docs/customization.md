# Customization

The engine ships with sensible defaults. This page covers the knobs available without modifying source.

## Title and description

```python
from wander_around import Wander
w = Wander(csv="data.csv", title="My Domain Atlas",
           description="Walking my company's product taxonomy.")
```

These appear on the landing page (`/`) and the welcome panel.

## Palette

Override colours per category (otherwise hashed from the category name):

```python
w = Wander(csv="data.csv", layout="ring", palette={
    "books":    "#a87520",
    "music":    "#3a78c4",
    "code":     "#2c4030",
    "people":   "#7a3a18",
    "_uncat":   "#6a6258",
})
```

Hex strings; any CSS-parseable colour works.

## Layout choice

```python
w = Wander(csv="data.csv", layout="ring")           # default; concentric per-category rings
w = Wander(csv="data.csv", layout="grid")           # uniform grid sorted by score
w = Wander(csv="data.csv", layout="passthrough")    # use x/y from CSV directly
w = Wander(csv="data.csv", layout="force",
           edges=[("a", "b"), ("b", "c")])          # force-directed (under 5K cards)
```

## Building height and saturation

`score` (a float column in your CSV) drives building height in 3D and dot radius in 2D. If absent, all buildings are uniform height.

```csv
id,label,category,score
big_thing,Big Thing,important,9.5
medium_thing,Medium Thing,important,3.0
```

To use a different column:

```python
w = Wander(csv="data.csv", building_height_field="popularity")
```

(planned — TODO; PR welcome)

## Embed in an existing FastAPI app

```python
from fastapi import FastAPI
from wander_around import Wander

w = Wander(csv="data.csv")
my_app = FastAPI()

# Mount under /walk so you keep your existing routes
my_app.mount("/walk", w.app())

# Now /walk/world is the 3D viewer, /walk/game is the 2D viewer
```

## Custom static path

The 3D world loads `three.module.js` from a CDN by default. To self-host:

```bash
# Find your install dir
python -c "import wander_around; print(wander_around.__file__)"

# Drop these into wander_around/static/:
#   three.module.js
#   PointerLockControls.js

# The server prefers local copies when present.
```

## Viewport-bounded data endpoint (for large datasets)

The default `/api/cards` returns the entire dataset. For datasets above ~50K rows, this is a few MB of JSON on every page load. Replace with a viewport-bounded version:

```python
from wander_around import Wander
from fastapi import Query

w = Wander(csv="big_dataset.csv")
app = w.app()

@app.get("/api/region")
async def region(cx: float, cy: float, r: float = 500,
                  limit: int = 500):
    near = [c for c in w.cards
             if (c.x - cx) ** 2 + (c.y - cy) ** 2 <= r * r]
    near.sort(key=lambda c: -(c.score or 0))
    return [c.to_dict() for c in near[:limit]]

# In your custom server.py replacement, point /api/cards at /api/region.
```

(A built-in viewport-bounded mode is on the roadmap.)
