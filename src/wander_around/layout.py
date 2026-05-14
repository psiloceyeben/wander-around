"""Layout algorithms: assign (x, y) coordinates to a list of Card if the
input data didn't already include them.

Algorithms:
    ring        — concentric rings grouped by category (default; matches the
                   wanderaround.io production layout)
    grid        — uniform grid sorted by score
    force       — force-directed graph (requires --edges)
    passthrough — leave (x, y) as-is; only validates that they're set

Each layout function takes a list[Card] and mutates it in place, setting
the x / y attributes. Returns the same list for chaining.
"""
from __future__ import annotations

import math
from collections import defaultdict
from .ingest import Card


def ring(cards: list[Card], radius_step: float = 60.0,
          spacing: float = 12.0) -> list[Card]:
    """Place cards in concentric rings grouped by category.

    Each category gets its own angular wedge; within a wedge, cards are
    distributed across rings outward from the centre. The result is a
    visual structure where similar-category cards cluster together and
    you can walk between districts.
    """
    by_cat: dict[str, list[Card]] = defaultdict(list)
    for c in cards:
        by_cat[c.category or "_uncat"].append(c)
    cats = sorted(by_cat)
    n_cats = max(len(cats), 1)
    wedge_step = (2 * math.pi) / n_cats
    for i, cat in enumerate(cats):
        items = by_cat[cat]
        items.sort(key=lambda c: -(c.score or 0))
        wedge_centre = i * wedge_step
        for j, card in enumerate(items):
            ring_idx = j // 16
            slot_in_ring = j % 16
            r = (ring_idx + 1) * radius_step
            theta = wedge_centre + (slot_in_ring - 8) * (wedge_step / 18)
            card.x = r * math.cos(theta)
            card.y = r * math.sin(theta)
    return cards


def grid(cards: list[Card], spacing: float = 24.0) -> list[Card]:
    """Place cards in a uniform square grid, sorted by score (highest first)."""
    sorted_cards = sorted(cards, key=lambda c: -(c.score or 0))
    n = len(sorted_cards)
    side = max(1, int(math.ceil(math.sqrt(n))))
    for idx, card in enumerate(sorted_cards):
        row, col = divmod(idx, side)
        card.x = (col - side / 2) * spacing
        card.y = (row - side / 2) * spacing
    return cards


def force(cards: list[Card],
          edges: list[tuple[str, str]] | None = None,
          iterations: int = 200,
          k: float = 30.0) -> list[Card]:
    """Force-directed layout. If edges is provided, related cards attract
    each other and repel unrelated ones. Without edges, falls back to grid.

    Implements a small Fruchterman-Reingold step loop. For datasets above
    ~5000 cards consider grid or ring instead — this is O(n²) per step.
    """
    if not edges:
        return grid(cards)
    # Force layout keys forces and lookups by Card.id; duplicates would
    # collapse force vectors and corrupt the simulation. Reject them
    # explicitly with a clear error rather than producing silently-wrong
    # output.
    seen_ids: set = set()
    for c in cards:
        if c.id in seen_ids:
            raise ValueError(
                f"force layout requires unique Card ids; duplicate found: {c.id!r}. "
                "Either deduplicate the dataset or use a different layout (ring/grid).")
        seen_ids.add(c.id)
    by_id = {c.id: c for c in cards}
    if not all(card.x is not None and card.y is not None for card in cards):
        # Random init around origin
        import random
        rng = random.Random(0xCAFE)
        for c in cards:
            if c.x is None:
                c.x = rng.uniform(-100, 100)
            if c.y is None:
                c.y = rng.uniform(-100, 100)
    edge_pairs = [(by_id[a], by_id[b]) for a, b in edges
                   if a in by_id and b in by_id]
    for _ in range(iterations):
        # Repulsion
        forces = {c.id: [0.0, 0.0] for c in cards}
        for i, a in enumerate(cards):
            for b in cards[i + 1:]:
                dx = a.x - b.x
                dy = a.y - b.y
                dist2 = dx * dx + dy * dy + 1e-3
                f = (k * k) / dist2
                fx = f * dx / math.sqrt(dist2)
                fy = f * dy / math.sqrt(dist2)
                forces[a.id][0] += fx
                forces[a.id][1] += fy
                forces[b.id][0] -= fx
                forces[b.id][1] -= fy
        # Attraction along edges
        for a, b in edge_pairs:
            dx = a.x - b.x
            dy = a.y - b.y
            dist = math.sqrt(dx * dx + dy * dy + 1e-3)
            f = (dist * dist) / k
            fx = f * dx / dist
            fy = f * dy / dist
            forces[a.id][0] -= fx
            forces[a.id][1] -= fy
            forces[b.id][0] += fx
            forces[b.id][1] += fy
        # Apply with cooling
        for c in cards:
            fx, fy = forces[c.id]
            mag = math.sqrt(fx * fx + fy * fy + 1e-9)
            step = min(mag, 5.0)
            c.x += (fx / mag) * step
            c.y += (fy / mag) * step
    return cards


def passthrough(cards: list[Card]) -> list[Card]:
    """Validate that every card already has (x, y) set. Errors otherwise."""
    missing = [c.id for c in cards if c.x is None or c.y is None]
    if missing:
        raise ValueError(
            f"passthrough layout requires every card to have (x, y); "
            f"{len(missing)} are missing — first few: {missing[:5]}")
    return cards


def apply(name: str, cards: list[Card], **kwargs) -> list[Card]:
    """Dispatch by layout name."""
    fn = {"ring": ring, "grid": grid, "force": force,
          "passthrough": passthrough}.get(name)
    if fn is None:
        raise ValueError(
            f"unknown layout {name!r}; choose from "
            f"ring, grid, force, passthrough")
    return fn(cards, **kwargs)
