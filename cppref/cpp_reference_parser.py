import html
import re
from sqlite3 import Connection

from requests import get

from cppref.page_parser import PageParser


class CppReferenceParser(PageParser):
    _known_pages = ("cpp", "c")

    def __init__(self, page: str, conn: Connection):
        if page not in self._known_pages:
            raise ValueError(f"Unsupported page: {page}")
        self._page = page
        self._conn = conn

    def populate_database(self, rank: int) -> None:
        url = f"https://en.cppreference.com/w/{self._page}/symbol_index"
        text = get(url).text
        psym = re.compile(
            r'^<a href="([^"]+)" title="[^"]+"><tt>([^<]+)</tt></a>', re.M
        )
        sym_prefix = "std::" if self._page == "cpp" else ""
        with self._conn:
            pid = self._conn.execute(
                "INSERT OR REPLACE INTO page (name, rank, url_prefix, url) VALUES (?, ?, ?, ?) RETURNING id",
                (self._page, rank, "https://en.cppreference.com", url),
            ).fetchone()[0]
            self._conn.executemany(
                "INSERT OR REPLACE INTO symbol (page_id, number, name, url) VALUES (?, ?, ?, ?)",
                (
                    (pid, i, sym_prefix + html.unescape(m[2]), m[1])
                    for i, m in enumerate(psym.finditer(text))
                ),
            )
