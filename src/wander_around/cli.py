"""Command-line interface — `wander-around serve --csv ...`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(
        prog="wander-around",
        description="Turn any 2D dataset into a walkable 3D world.")
    sub = p.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="serve a dataset as a walkable world")
    serve.add_argument("--csv", type=str, default=None,
                        help="path to a CSV file to walk")
    serve.add_argument("--jsonl", type=str, default=None,
                        help="path to a JSONL file (one JSON object per line)")
    serve.add_argument("--layout", type=str, default="ring",
                        choices=["ring", "grid", "force", "passthrough"],
                        help="layout algorithm (default: ring)")
    serve.add_argument("--edges", type=str, default=None,
                        help="path to a CSV with columns (source, target) — "
                             "required for layout=force")
    serve.add_argument("--host", type=str, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--title", type=str, default="Wander Around")

    info = sub.add_parser("info", help="describe a dataset without serving")
    info.add_argument("--csv", type=str, default=None)
    info.add_argument("--jsonl", type=str, default=None)

    args = p.parse_args()

    if args.cmd == "serve":
        if not args.csv and not args.jsonl:
            p.error("serve requires --csv or --jsonl")
        edges = None
        if args.edges:
            edges = _load_edges(args.edges)
        from .core import Wander
        w = Wander(
            csv=args.csv, jsonl=args.jsonl,
            layout=args.layout, edges=edges,
            title=args.title)
        url = f"http://{args.host}:{args.port}"
        print(f"wander-around serving {len(w.cards):,} entities at {url}")
        print(f"  /game  — 2D ring city")
        print(f"  /world — 3D walkable world")
        w.serve(host=args.host, port=args.port)
        return 0

    if args.cmd == "info":
        if not args.csv and not args.jsonl:
            p.error("info requires --csv or --jsonl")
        from . import ingest
        cards = (ingest.load_csv(args.csv) if args.csv
                  else ingest.load_jsonl(args.jsonl))
        cats: dict[str, int] = {}
        for c in cards:
            cats[c.category or "_uncat"] = cats.get(c.category or "_uncat", 0) + 1
        print(f"{len(cards):,} cards in {Path(args.csv or args.jsonl).name}")
        print(f"categories ({len(cats)}):")
        for cat, n in sorted(cats.items(), key=lambda kv: -kv[1])[:20]:
            print(f"  {n:>6,}  {cat}")
        return 0

    return 1


def _load_edges(path: str) -> list[tuple[str, str]]:
    import csv as _csv
    edges: list[tuple[str, str]] = []
    with open(path, encoding="utf-8") as fh:
        reader = _csv.DictReader(fh)
        for row in reader:
            src = (row.get("source") or row.get("src") or row.get("from")
                   or row.get("a"))
            dst = (row.get("target") or row.get("dst") or row.get("to")
                   or row.get("b"))
            if src and dst:
                edges.append((str(src), str(dst)))
    return edges


if __name__ == "__main__":
    sys.exit(main())
