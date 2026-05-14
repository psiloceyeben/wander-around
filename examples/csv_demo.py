"""Tiny demo: 50 great books → walkable 3D world in one command.

Uses examples/demo_books.csv (shipped with the repo). Run from this
directory:

    python csv_demo.py
"""
from pathlib import Path
from wander_around import Wander

data_path = Path(__file__).parent / "demo_books.csv"

w = Wander(csv=str(data_path), layout="ring", title="Demo Library")
print(f"loaded {len(w.cards)} cards in {len(set(c.category for c in w.cards))} categories")
print(f"open http://localhost:8000/world to walk in (3D)")
print(f"open http://localhost:8000/game to see the 2D top-down map")
w.serve(host="127.0.0.1", port=8000)
