"""Conexión a SQL Server con reintento de driver ODBC."""

from __future__ import annotations

import re
from typing import Iterator

import pandas as pd
import pyodbc

from config import get_connection_string


def _connection_strings() -> Iterator[str]:
    base = get_connection_string()
    yield base
    for driver in ("ODBC Driver 17 for SQL Server", "SQL Server"):
        yield re.sub(
            r"DRIVER=\{[^}]+\}",
            f"DRIVER={{{driver}}}",
            base,
            count=1,
        )


def get_connection():
    last_err: Exception | None = None
    for conn_str in _connection_strings():
        try:
            return pyodbc.connect(conn_str, timeout=15)
        except Exception as e:
            last_err = e
            continue
    raise last_err  # type: ignore[misc]


def read_sql(query: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql(query, conn)
