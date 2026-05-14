"""Wander Around — turn any 2D dataset into a walkable 3D world.

Quickstart:

    from wander_around import Wander
    w = Wander(csv="my_data.csv", layout="ring")
    w.serve()

CLI:

    wander-around serve --csv my_data.csv --layout ring

The engine is the open-source half of the wanderaround.io project; the
substrate-augmented language model that lives inside the production
deployment is published separately at github.com/Prometheus7/wander-substrate.
"""

__version__ = "0.1.0"

from .core import Wander  # noqa: F401
from .ingest import load_csv, load_jsonl, Card  # noqa: F401
from . import layout  # noqa: F401

__all__ = ["Wander", "load_csv", "load_jsonl", "Card", "layout", "__version__"]
