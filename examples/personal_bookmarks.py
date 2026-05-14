"""Walk your browser bookmark export as a 3D world.

Pass the path to a Netscape-format bookmarks HTML file (Firefox / Chrome
both export this from Settings → Bookmarks → Export):

    python personal_bookmarks.py ~/Downloads/bookmarks.html
"""
import sys
import re
from html.parser import HTMLParser
from pathlib import Path

from wander_around import Wander, Card


class BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_folder = "Root"
        self.folder_stack = ["Root"]
        self.cards: list[Card] = []
        self.in_a = False
        self.current_href = ""
        self.text_buffer = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3":
            self.text_buffer = ""
        elif tag == "a":
            self.in_a = True
            self.current_href = attrs.get("href", "")
            self.text_buffer = ""
        elif tag == "dl":
            # Nested folder begins
            self.folder_stack.append(self.current_folder)

    def handle_endtag(self, tag):
        if tag == "h3":
            self.current_folder = self.text_buffer.strip()[:30] or "Root"
        elif tag == "a" and self.in_a:
            label = self.text_buffer.strip()
            if self.current_href and label:
                self.cards.append(Card(
                    id=self.current_href,
                    label=label[:80],
                    category=self.current_folder,
                    link=self.current_href,
                ))
            self.in_a = False
        elif tag == "dl":
            if len(self.folder_stack) > 1:
                self.current_folder = self.folder_stack.pop()

    def handle_data(self, data):
        self.text_buffer += data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python personal_bookmarks.py <bookmarks.html>")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"file not found: {path}")
        sys.exit(1)
    parser = BookmarkParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    cards = parser.cards
    print(f"loaded {len(cards)} bookmarks in "
          f"{len(set(c.category for c in cards))} folders")
    w = Wander(cards=cards, layout="ring",
                title=f"My Bookmarks ({path.stem})")
    print(f"\nopen http://localhost:8000/world")
    w.serve(host="127.0.0.1", port=8000)
