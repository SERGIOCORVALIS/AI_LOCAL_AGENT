from __future__ import annotations

from html.parser import HTMLParser

from packages.perception import WebDocument


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._capture_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._capture_title = False

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self.title += data


class WebParser:
    def parse_html(self, url: str, html: str) -> WebDocument:
        parser = _TitleParser()
        parser.feed(html)
        markdown = html.replace("<p>", "").replace("</p>", "\n").strip()
        return WebDocument(url=url, title=parser.title.strip() or "Untitled", markdown=markdown)
