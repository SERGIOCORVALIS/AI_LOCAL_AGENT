from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx

from packages.perception import WebDocument, WebSearchResponse, WebSearchResult

DDG_HTML_URL = "https://html.duckduckgo.com/html/"


class _HtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_title = False
        self._skip_depth = 0
        self.title = ""
        self.chunks: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if lowered == "title":
            self._capture_title = True
        if lowered == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if lowered in {"p", "h1", "h2", "h3", "li", "br", "div"}:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if lowered == "title":
            self._capture_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._capture_title:
            self.title += text
        else:
            self.chunks.append(text)


class _DuckDuckGoResultsParser(HTMLParser):
    """Extract organic results from DuckDuckGo HTML endpoint markup."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[WebSearchResult] = []
        self._result_depth = 0
        self._capture_title = False
        self._capture_snippet = False
        self._current_url = ""
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        classes = set(attrs_dict.get("class", "").split())
        lowered = tag.lower()

        if lowered == "div" and "web-result" in classes and "result--ad" not in classes:
            self._commit()
            self._result_depth = 1
            self._current_url = ""
            self._title_parts = []
            self._snippet_parts = []
            return

        if self._result_depth <= 0:
            return

        if lowered == "div":
            self._result_depth += 1

        if lowered == "a" and "result__a" in classes:
            href = attrs_dict.get("href", "")
            self._current_url = _unwrap_ddg_redirect(href)
            self._capture_title = True
            return

        if lowered in {"a", "td"} and "result__snippet" in classes:
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "a" and self._capture_title:
            self._capture_title = False
        if lowered in {"a", "td"} and self._capture_snippet:
            self._capture_snippet = False
        if lowered == "div" and self._result_depth > 0:
            self._result_depth -= 1
            if self._result_depth == 0:
                self._commit()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._capture_title:
            self._title_parts.append(text)
        elif self._capture_snippet:
            self._snippet_parts.append(text)

    def close(self) -> None:
        self._commit()
        super().close()

    def _commit(self) -> None:
        if self._current_url and self._title_parts:
            self.results.append(
                WebSearchResult(
                    title=unescape(" ".join(self._title_parts)).strip(),
                    url=self._current_url,
                    snippet=unescape(" ".join(self._snippet_parts)).strip(),
                )
            )
        self._result_depth = 0
        self._capture_title = False
        self._capture_snippet = False
        self._current_url = ""
        self._title_parts = []
        self._snippet_parts = []


def _unwrap_ddg_redirect(href: str) -> str:
    if not href:
        return ""
    absolute = urljoin(DDG_HTML_URL, href)
    parsed = urlparse(absolute)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        uddg = query.get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    return absolute


def parse_duckduckgo_html(html: str, *, max_results: int = 5) -> list[WebSearchResult]:
    parser = _DuckDuckGoResultsParser()
    parser.feed(html)
    parser.close()
    # Deduplicate by URL while preserving order.
    seen: set[str] = set()
    unique: list[WebSearchResult] = []
    for item in parser.results:
        if item.url in seen:
            continue
        seen.add(item.url)
        unique.append(item)
        if len(unique) >= max_results:
            break
    return unique


class WebParser:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=15.0, follow_redirects=True)

    def fetch_url(self, url: str) -> WebDocument:
        response = self._client.get(url)
        response.raise_for_status()
        return self.parse_html(url, response.text)

    def parse_html(self, url: str, html: str) -> WebDocument:
        extractor = _HtmlExtractor()
        extractor.feed(html)
        text = " ".join(extractor.chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        markdown = f"# {extractor.title.strip() or 'Untitled'}\n\n{text}"
        absolute_links = sorted(
            {
                urljoin(url, link)
                for link in extractor.links
                if link and not link.startswith("#")
            }
        )
        return WebDocument(
            url=url,
            title=extractor.title.strip() or "Untitled",
            markdown=markdown,
            links=absolute_links,
        )

    def search(self, query: str, *, max_results: int = 5) -> WebSearchResponse:
        cleaned = query.strip()
        if not cleaned:
            return WebSearchResponse(query=query, results=[])
        response = self._client.post(
            DDG_HTML_URL,
            data={"q": cleaned, "b": ""},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; LocalAIAgent/1.0; +https://localhost)"
                )
            },
        )
        response.raise_for_status()
        results = parse_duckduckgo_html(response.text, max_results=max_results)
        return WebSearchResponse(query=cleaned, provider="duckduckgo", results=results)
