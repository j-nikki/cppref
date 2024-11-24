from abc import ABC, abstractmethod
from sqlite3 import Connection

SCHEMA_VERSION = 1

base_schema = """
CREATE TABLE IF NOT EXISTS page (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (name <> ''),
    rank INTEGER NOT NULL UNIQUE,
    url_prefix TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    fetched_at INTEGER NOT NULL DEFAULT (unixepoch())
) STRICT;

CREATE TABLE IF NOT EXISTS symbol (
    page_id INTEGER NOT NULL REFERENCES page(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    name TEXT NOT NULL CHECK (name <> ''),
    url TEXT NOT NULL CHECK (url <> ''),
    PRIMARY KEY (page_id, number),
    UNIQUE (page_id, name),
    UNIQUE (page_id, number)
) WITHOUT ROWID, STRICT;
"""


class PageParser(ABC):
    @abstractmethod
    def __init__(self, page: str, conn: Connection):
        """
        Initializes the page parser.

        :param page: The name of the page.
        :param conn: The database connection.
        """
        pass

    @abstractmethod
    def populate_database(self, rank: int) -> None:
        """
        Populates the database with data fetched from the given URL.

        :param rank: The rank of the page - lower ranks take precedence.
        """
        pass


class SymbolQuery:
    def __init__(self, conn: Connection):
        """
        Initializes the symbol query.

        :param conn: The database connection.
        """
        self._conn = conn
        self._known_pages = [
            name
            for (name,) in conn.execute("SELECT DISTINCT name FROM page").fetchall()
        ]

    def query_symbols(self, /, pages: list[str] = []) -> list[str]:
        """
        Queries the symbols from the database for the given pages.

        :param pages: The pages to query symbols for.
        :return: A list of tuples containing name and URL of each matching symbol.
        """
        if unk := set(pages) - set(self._known_pages):
            raise ValueError(f"Unsupported pages: {unk}")
        pages = pages or self._known_pages
        return [
            name
            for (name,) in self._conn.execute(
                f"""
            SELECT DISTINCT s.name
            FROM page p
            JOIN symbol s ON p.id = s.page_id
            WHERE p.name IN ({','.join(['?'] * len(pages))})
            ORDER BY p.rank, s.number
            """,
                (*pages,),
            )
        ]

    def query_symbol_url(
        self, symbol_name: str, /, pages: list[str] = []
    ) -> list[tuple[int, str, str]]:
        """
        Queries matching symbols from the database for the given pages and symbol pattern.

        :param symbol_name: The name of the symbol.
        :param pages: The pages to search for the symbol.
        :return: A list of tuples containing number, name, and URL of each matching symbol.
        """
        if unk := set(pages) - set(self._known_pages):
            raise ValueError(f"Unsupported pages: {unk}")
        pages = pages or self._known_pages
        result = self._conn.execute(
            f"""
            WITH ranked_symbols AS (
                SELECT 
                    s.number, 
                    s.name, 
                    p.url_prefix || s.url AS full_url,
                    ROW_NUMBER() OVER (PARTITION BY s.name ORDER BY p.rank) AS rn
                FROM page p
                JOIN symbol s ON p.id = s.page_id
                WHERE p.name IN ({','.join(['?'] * len(pages))}) AND s.name LIKE ?
            )
            SELECT number, name, full_url
            FROM ranked_symbols
            WHERE rn = 1
            """,
            (*pages, symbol_name),
        ).fetchall()
        return result
