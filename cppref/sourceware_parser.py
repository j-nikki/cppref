import html
import re
from sqlite3 import Connection

from requests import get

from cppref.page_parser import PageParser


class SourcewareParser(PageParser):
    _known_pages = ("glibc",)

    def __init__(self, page: str, conn: Connection):
        if page not in self._known_pages:
            raise ValueError(f"Unsupported page: {page}")
        self._page = page
        self._conn = conn

    def populate_database(self, rank: int) -> None:
        url = "https://sourceware.org/glibc/manual/latest/html_node/Function-Index.html"
        text = get(url).text
        psym = re.compile(
            r'^<tr><td></td><td class="printindex-index-entry"><a href="([^"]+)"><code>([^<]+)</code></a></td>',
            re.M,
        )
        with self._conn:
            pid = self._conn.execute(
                "INSERT OR REPLACE INTO page (name, rank, url_prefix, url) VALUES (?, ?, ?, ?) RETURNING id",
                (
                    self._page,
                    rank,
                    "https://sourceware.org/glibc/manual/latest/html_node/",
                    url,
                ),
            ).fetchone()[0]
            self._conn.executemany(
                "INSERT OR REPLACE INTO symbol (page_id, number, name, url) VALUES (?, ?, ?, ?)",
                (
                    (pid, i, html.unescape(m[2]), m[1])
                    for i, m in enumerate(psym.finditer(text))
                ),
            )
