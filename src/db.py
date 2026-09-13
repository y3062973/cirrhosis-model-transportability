"""Database connection for the public release.

Credentials are NEVER stored in this repository. They are read from environment
variables so that no password, host or username is committed:

    DB_HOST      database server host
    DB_PORT      database server port (default 5432)
    DB_USER      database user
    DB_PASSWORD  database password
    DB_NAME      database name, or use the per-database helpers below

Copy `.env.example` to `.env` and fill it in locally. `.env` is git-ignored.

The three source databases are accessed under their own credentialed agreements:
MIMIC-IV v3.1 and eICU-CRD v2.0 through PhysioNet, and nwICU v0.1.0 through its
custodial access process. See DATA_ACCESS.md.
"""
from __future__ import annotations

import os


def _require(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise SystemExit(
            f"environment variable {name} is not set. Copy .env.example to .env, "
            f"fill it in, and export it (or use python-dotenv). No credentials are "
            f"stored in this repository by design.")
    return v


def connect(dbname: str | None = None, readonly: bool = True):
    """Open a psycopg2 connection using environment credentials.

    Defaults to a READ-ONLY session, because every query in this release reads and
    none writes.
    """
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5432")),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
        dbname=dbname or _require("DB_NAME"),
        connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "20")),
    )
    if readonly:
        conn.set_session(readonly=True)
    return conn


# The three databases used by the study. Keep these names configurable rather than
# hardcoded, because a reader's local installation will name them differently.
def mimic(dbname: str | None = None):
    return connect(dbname or os.environ.get("DB_NAME_MIMIC", "mimiciv3"))


def eicu(dbname: str | None = None):
    return connect(dbname or os.environ.get("DB_NAME_EICU", "eicu"))


def nwicu(dbname: str | None = None):
    return connect(dbname or os.environ.get("DB_NAME_NWICU", "nwicu"))
