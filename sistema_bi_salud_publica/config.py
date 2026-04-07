"""Configuración de conexión a SQL Server."""

import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)


def get_connection_string() -> str:
    """
    - SQLSERVER_AUTH=windows (por defecto): Trusted_Connection, sin UID/PWD.
      Usa la misma sesión de Windows que SSMS (ej. ALE\\Usuario).
    - SQLSERVER_AUTH=sql: requiere SQLSERVER_USER y SQLSERVER_PASSWORD (login SQL).
    """
    host = os.getenv("SQLSERVER_HOST", "localhost").strip()
    port_raw = os.getenv("SQLSERVER_PORT", "").strip()
    # Solo usar puerto si es numérico (evita typos como "w" que rompen SERVER=host,puerto)
    port = port_raw if port_raw.isdigit() else ""
    database = os.getenv("SQLSERVER_DATABASE", "BI_SaludPublica_Bolivia").strip()
    user = os.getenv("SQLSERVER_USER", "").strip()
    password = os.getenv("SQLSERVER_PASSWORD", "").strip()
    auth = os.getenv("SQLSERVER_AUTH", "windows").strip().lower()

    if auth in ("sql", "usuario"):
        if not user or not password:
            raise ValueError(
                "Con SQLSERVER_AUTH=sql debes definir SQLSERVER_USER y SQLSERVER_PASSWORD."
            )
        use_sql_login = True
    else:
        use_sql_login = False

    if port:
        server = f"{host},{port}"
    else:
        server = host

    driver = os.getenv("SQLSERVER_ODBC_DRIVER", "ODBC Driver 18 for SQL Server").strip()

    if use_sql_login:
        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={server}",
            f"DATABASE={database}",
            f"UID={user}",
            f"PWD={password}",
            "TrustServerCertificate=yes",
        ]
    else:
        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={server}",
            f"DATABASE={database}",
            "Trusted_Connection=yes",
            "TrustServerCertificate=yes",
        ]

    return ";".join(parts)
