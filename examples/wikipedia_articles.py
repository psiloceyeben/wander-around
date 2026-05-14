"""Walk the first 5,000 Simple English Wikipedia articles as a 3D world.

Downloads the Simple-Wiki dump (about 200 MB) on first run, extracts the
first 5,000 article titles + categories, then serves them as a walkable
city.
"""
import bz2
import os
import sys
from pathlib import Path
from urllib.request import urlretrieve
from xml.etree.ElementTree import iterparse

from wander_around import Wander, Card

DUMP_URL = "https://dumps.wikimedia.org/simplewiki/latest/simplewiki-latest-pages-articles.xml.bz2"
DUMP_PATH = Path(__file__).parent / "simplewiki.xml.bz2"
N_ARTICLES = 5000


def fetch_dump() -> Path:
    if DUMP_PATH.exists():
        return DUMP_PATH
    print(f"downloading {DUMP_URL} ({DUMP_PATH}) ~200 MB ...")
    urlretrieve(DUMP_URL, DUMP_PATH)
    return DUMP_PATH


def extract_articles(path: Path, n: int) -> list[Card]:
    NS = "{http://www.mediawiki.org/xml/export-0.11/}"
    cards: list[Card] = []
    with bz2.open(path, "rb") as fh:
        for ev, elem in iterparse(fh, events=("end",)):
            if elem.tag != NS + "page":
                continue
            ns_el = elem.find(NS + "ns")
            if ns_el is not None and ns_el.text != "0":
                elem.clear(); continue
            title_el = elem.find(NS + "title")
            if title_el is None or not title_el.text:
                elem.clear(); continue
            text_el = elem.find(NS + "revision/" + NS + "text")
            body = text_el.text if text_el is not None else ""
            # Crude category extraction
            cats = []
            if body:
                for line in body.split("\n"):
                    if line.startswith("[[Category:"):
                        cats.append(line[11:line.find("]", 11) if "]" in line else 11].strip()[:30])
            cat = cats[0] if cats else "Uncategorized"
            cards.append(Card(
                id=title_el.text,
                label=title_el.text,
                category=cat,
                score=len(body) / 1000.0 if body else 0.0,
                link=f"https://simple.wikipedia.org/wiki/{title_el.text.replace(' ', '_')}",
            ))
            elem.clear()
            if len(cards) >= n:
                break
    return cards


if __name__ == "__main__":
    path = fetch_dump()
    print(f"extracting first {N_ARTICLES} articles...")
    cards = extract_articles(path, N_ARTICLES)
    print(f"loaded {len(cards)} articles in "
          f"{len(set(c.category for c in cards))} categories")
    w = Wander(cards=cards, layout="ring",
                title="Simple Wikipedia (5K articles)")
    print(f"\nopen http://localhost:8000/world to walk Wikipedia in 3D")
    w.serve(host="127.0.0.1", port=8000)
