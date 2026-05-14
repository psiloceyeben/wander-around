"""Loading 2D datasets from CSV / JSONL into the engine's card model.

Every entity rendered by the engine is a Card: a small dataclass with an id,
a display label, optional 2D coordinates (assigned by the layout module if
absent), and optional category / score / link / image fields that drive
colouring, building height, click-action, and facade texture respectively.

The ingest functions return a plain list[Card]; everything downstream
(layout, server, client) operates on that list.
"""
from __future__ import annotations

import csv as _csv
import json as _json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Card:
    """One placed entity in the wandered world."""
    id: str
    label: str
    x: float | None = None
    y: float | None = None
    category: str | None = None
    score: float | None = None
    link: str | None = None
    image_url: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y,
        }
        if self.category is not None:
            d["category"] = self.category
        if self.score is not None:
            d["score"] = self.score
        if self.link is not None:
            d["link"] = self.link
        if self.image_url is not None:
            d["image_url"] = self.image_url
        if self.extra:
            d["extra"] = self.extra
        return d


def _coerce_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _row_to_card(row: dict) -> Card:
    return Card(
        id=str(row.get("id") or row.get("ID") or row.get("Id")
                or row.get("uid") or ""),
        label=str(row.get("label") or row.get("Label")
                  or row.get("name") or row.get("title") or ""),
        x=_coerce_float(row.get("x") or row.get("X")),
        y=_coerce_float(row.get("y") or row.get("Y")),
        category=(row.get("category") or row.get("Category")
                  or row.get("type") or row.get("class")) or None,
        score=_coerce_float(row.get("score") or row.get("Score")
                              or row.get("rank") or row.get("rating")),
        link=row.get("link") or row.get("url") or row.get("URL"),
        image_url=row.get("image_url") or row.get("image")
                   or row.get("thumbnail"),
        extra={k: v for k, v in row.items()
                if k not in {"id", "label", "x", "y", "category", "score",
                              "link", "image_url",
                              "ID", "Id", "Label", "X", "Y", "Category",
                              "Score", "name", "title", "type", "class",
                              "url", "URL", "image", "thumbnail",
                              "rank", "rating", "uid"}},
    )


def load_csv(path: str | Path) -> list[Card]:
    """Load a CSV file into a list of Card. Every row becomes one Card.

    The id and label columns are required (the engine errors if every row
    is missing both). All other columns are optional.

    Coordinate columns x, y are read as floats if present; otherwise the
    layout module assigns coordinates downstream.
    """
    cards: list[Card] = []
    with open(path, encoding="utf-8") as fh:
        reader = _csv.DictReader(fh)
        for row in reader:
            cards.append(_row_to_card(row))
    if cards and not any(c.id or c.label for c in cards):
        raise ValueError(
            f"{path}: no rows with id or label — engine requires at "
            f"least one of those columns")
    # Backfill empty ids with row-index-based defaults so the engine
    # never has to handle id-less cards.
    for i, c in enumerate(cards):
        if not c.id:
            c.id = f"row_{i}"
        if not c.label:
            c.label = c.id
    return cards


def load_jsonl(path: str | Path) -> list[Card]:
    """Load a JSON-lines file (one JSON object per line) into a list of Card."""
    cards: list[Card] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = _json.loads(line)
            if not isinstance(obj, dict):
                continue
            cards.append(_row_to_card(obj))
    for i, c in enumerate(cards):
        if not c.id:
            c.id = f"row_{i}"
        if not c.label:
            c.label = c.id
    return cards


def cards_from_iter(rows: Iterable[dict]) -> list[Card]:
    """Build cards from any iterable of dicts (e.g., a database query)."""
    cards = [_row_to_card(r) for r in rows]
    for i, c in enumerate(cards):
        if not c.id:
            c.id = f"row_{i}"
        if not c.label:
            c.label = c.id
    return cards
