"""Capa Silver: limpieza y estandarización (calidad de datos para analítica)."""

from __future__ import annotations

import pandas as pd


def _clean_text(s: pd.Series) -> pd.Series:
    if s.dtype != object:
        return s
    mask = s.notna()
    out = s.copy()
    out.loc[mask] = (
        s.loc[mask]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    return out


def _title_words(s: pd.Series) -> pd.Series:
    m = s.notna() & (s.astype(str).str.strip() != "") & (s.astype(str) != "nan")
    out = s.copy()
    out.loc[m] = s.loc[m].astype(str).str.title()
    return out


def transform_eventos_silver(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in (
        "PacienteNombres",
        "PacienteApellidos",
        "EnfermedadPrincipal",
        "HospitalOrigen",
        "HospitalDestino",
        "DepartamentoOrigen",
        "CiudadOrigen",
    ):
        if col in out.columns:
            out[col] = _clean_text(out[col])
            if col in ("PacienteNombres", "PacienteApellidos"):
                out[col] = _title_words(out[col])

    if "DiagnosticoSecundario" in out.columns:
        out["DiagnosticoSecundario"] = _clean_text(out["DiagnosticoSecundario"])
        out.loc[out["DiagnosticoSecundario"].isin(["", "nan", "None"]), "DiagnosticoSecundario"] = pd.NA

    if "Observaciones" in out.columns:
        out["Observaciones"] = _clean_text(out["Observaciones"])
        out.loc[out["Observaciones"].isin(["", "nan", "None"]), "Observaciones"] = pd.NA

    if "CanalIngreso" in out.columns:
        out["CanalIngreso"] = _clean_text(out["CanalIngreso"])
        out.loc[out["CanalIngreso"].isin(["", "nan", "None"]), "CanalIngreso"] = pd.NA

    out["FechaEvento"] = pd.to_datetime(out["FechaEvento"], errors="coerce")
    out["Anio"] = out["FechaEvento"].dt.year
    out["Mes"] = out["FechaEvento"].dt.month

    return out
