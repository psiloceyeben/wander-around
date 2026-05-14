"""The Wander class — main entry point. Holds a dataset of cards and
exposes a serve() method that runs the FastAPI app."""
from __future__ import annotations

from pathlib import Path

from . import ingest, layout
from .ingest import Card


class Wander:
    """Top-level engine instance.

    Common usage:

        w = Wander(csv="my_data.csv", layout="ring")
        w.serve(host="0.0.0.0", port=8000)

    Programmatic dataset:

        cards = [Card(id="a", label="Alpha", category="x"), ...]
        w = Wander(cards=cards, layout="grid")
        w.serve()
    """

    def __init__(self,
                 csv: str | Path | None = None,
                 jsonl: str | Path | None = None,
                 cards: list[Card] | None = None,
                 layout: str = "ring",
                 edges: list[tuple[str, str]] | None = None,
                 palette: dict[str, str] | None = None,
                 title: str = "Wander Around",
                 description: str = "A walkable cartography of your dataset.",
                 ) -> None:
        if cards is not None:
            self.cards = list(cards)
        elif csv is not None:
            self.cards = ingest.load_csv(csv)
        elif jsonl is not None:
            self.cards = ingest.load_jsonl(jsonl)
        else:
            raise ValueError(
                "must pass one of: cards=, csv=, or jsonl=")
        self.layout_name = layout
        self.edges = edges
        layout_kwargs: dict = {}
        if layout == "force" and edges:
            layout_kwargs["edges"] = edges
        from . import layout as _layout_mod
        _layout_mod.apply(layout, self.cards, **layout_kwargs)
        self.palette = palette or {}
        self.title = title
        self.description = description

    def serve(self, host: str = "127.0.0.1", port: int = 8000,
               reload: bool = False) -> None:
        """Block and serve the engine over HTTP. Defaults to localhost:8000."""
        import uvicorn
        from . import server
        app = server.build_app(self)
        uvicorn.run(app, host=host, port=port, reload=reload)

    def app(self):
        """Return the FastAPI app object without serving — useful for embedding
        the engine inside an existing FastAPI deployment, mounting under a
        path prefix, etc."""
        from . import server
        return server.build_app(self)
