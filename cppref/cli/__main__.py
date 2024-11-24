import os
import sys
from argparse import ArgumentParser
from sqlite3 import connect

from cppref.cpp_reference_parser import *
from cppref.page_parser import *
from cppref.sourceware_parser import *

_cache_dir = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache")) + "/cppref"


def main() -> None:
    known_parsers: dict[str, tuple[type[PageParser], int]] = {
        "cpp": (CppReferenceParser, 0),
        "c": (CppReferenceParser, 1),
        "glibc": (SourcewareParser, 2),
    }
    parser_choices = list(known_parsers.keys())

    ap = ArgumentParser(
        description="Command-line tool for fetching and querying C++ and C symbol indices from cppreference.com and glibc symbol index from sourceware.org."
    )
    subparsers = ap.add_subparsers(dest="command", help="Subcommands")

    fetch_parser = subparsers.add_parser(
        "fetch", help="Fetch symbols from the specified pages"
    )
    fetch_parser.add_argument(
        "-C",
        "--ignore-cache",
        action="store_true",
        help="Ignore the cache and fetch symbols from the web",
    )
    fetch_parser.add_argument(
        "-p",
        "--page-names",
        choices=parser_choices,
        nargs="*",
        default=parser_choices,
        help="Specify the pages to fetch symbols from. If none are specified, all known pages will be used.",
    )

    url_parser = subparsers.add_parser(
        "url", help="Query the URL of a symbol from the specified pages"
    )
    url_parser.add_argument(
        "-p",
        "--page-names",
        choices=parser_choices,
        nargs="*",
        default=parser_choices,
        help="Specify the pages to query symbols from. If none are specified, all known pages will be used.",
    )
    url_parser.add_argument(
        "symbol_name",
        metavar="symbol-name",
        type=str,
        help="The name of the symbol to query",
    )

    args = ap.parse_args()

    if not os.path.exists(_cache_dir):
        os.mkdir(_cache_dir)
    with connect(f"{_cache_dir}/cppref.db") as conn:
        if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            conn.executescript(
                """
                PRAGMA writable_schema = 1;
                DELETE FROM sqlite_master WHERE type IN ('table', 'index', 'trigger');
                PRAGMA writable_schema = 0;
                VACUUM;
                """
            )
        conn.executescript(
            f"""
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            BEGIN;
            PRAGMA foreign_keys = ON;
            PRAGMA user_version = {SCHEMA_VERSION};
            {base_schema}
            COMMIT;
        """
        )

        pages: list[str] = args.page_names if args.page_names else parser_choices
        parsers = [
            (name, pfact(name, conn), rank)
            for name, (pfact, rank) in known_parsers.items()
            if name in pages
        ]

        if args.command == "fetch":
            for name, parser, rank in parsers:
                old = (
                    (True,)
                    if args.ignore_cache
                    else conn.execute(
                        "SELECT fetched_at < (unixepoch() - 7 * 24 * 60 * 60) FROM page WHERE name = ?",
                        (name,),
                    ).fetchone()
                )
                if not old or old[0]:
                    parser.populate_database(rank)
            q = SymbolQuery(conn)
            sys.stdout.write("\n".join(q.query_symbols()) + "\n")
        elif args.command == "url":
            name_likes = [
                args.symbol_name,
                f"{args.symbol_name}%",
                f"%{args.symbol_name}%",
            ]
            q = SymbolQuery(conn)
            for result in (q.query_symbol_url(nl) for nl in name_likes):
                if len(result) > 1:
                    print("Multiple symbols found:", file=sys.stderr)
                    sznum = len(str(len(result)))
                    szname = max(len(name) for _num, name, _url in result)
                    for i, (_num, name, url) in enumerate(result):
                        print(
                            f"{i + 1:{sznum}}. {name:{szname}} {url}", file=sys.stderr
                        )
                    print("Please be more specific.", file=sys.stderr)
                    exit(1)
                elif len(result) == 1:
                    print(result[0][2])
                    exit(0)
            else:
                print(
                    f"Symbol '{args.symbol_name}' not found",
                    file=sys.stderr,
                )
                exit(1)


if __name__ == "__main__":
    main()
