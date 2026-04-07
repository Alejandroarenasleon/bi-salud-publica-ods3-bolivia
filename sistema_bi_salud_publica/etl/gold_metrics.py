"""Capa Gold: KPIs alineados al proyecto (referencias, tiempos, epidemiología, ODS 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class KPIBundle:
    tiempo_espera_promedio_min: float
    tiempo_espera_meta_min: float
    pct_referencias_exitosas: float
    pct_meta_referencias: float
    ocupacion_camas_estimada_pct: float
    ocupacion_meta_pct: float
    medicamentos_alto_riesgo: int
    costo_total_periodo_bs: float
    total_eventos: int


def indicadores_ods3_referencia() -> dict[str, Any]:
    """Valores de referencia del PDF (comparativo regional / metas)."""
    return {
        "mmr_bolivia_2020": 160.9,
        "mmr_bolivia_est_2023": 146.4,
        "mmr_regional_promedio": 87.6,
        "mortalidad_infantil_2022": 20.44,
        "meta_reduccion_mortalidad_evitable_pct": 15.0,
        "meta_desabastecimiento_pct": 20.0,
        "ods": "ODS 3 — Salud y bienestar",
    }


def compute_kpis(df: pd.DataFrame) -> KPIBundle:
    d = df.copy()
    total = len(d)
    if total == 0:
        return KPIBundle(
            tiempo_espera_promedio_min=0.0,
            tiempo_espera_meta_min=120.0,
            pct_referencias_exitosas=0.0,
            pct_meta_referencias=95.0,
            ocupacion_camas_estimada_pct=0.0,
            ocupacion_meta_pct=80.0,
            medicamentos_alto_riesgo=0,
            costo_total_periodo_bs=0.0,
            total_eventos=0,
        )

    esp = d["TiempoEsperaMin"].dropna()
    tiempo_prom = float(esp.mean()) if len(esp) else 0.0

    ref = d[d["TipoEvento"] == "Referencia"]
    if len(ref):
        ok = ref[ref["EstadoAtencion"] == "Atendido"]
        pct_ref_ok = float(len(ok) / len(ref) * 100)
    else:
        pct_ref_ok = 0.0

    hosp = d[d["TipoEvento"] == "Hospitalizacion"]
    if len(hosp) and "CamasHospitalOrigen" in d.columns:
        by_h = (
            hosp.groupby(["HospitalOrigenID", "CamasHospitalOrigen"], dropna=False)
            .size()
            .reset_index(name="eventos_hosp")
        )
        ratios = (by_h["eventos_hosp"] / by_h["CamasHospitalOrigen"].clip(lower=1)) * 100
        ocup = float(ratios.clip(upper=100).mean())
    else:
        ocup = 0.0

    farm = d[d["TipoEvento"].isin(["Farmacia", "Hospitalizacion", "Emergencia"])]
    farm = farm.dropna(subset=["MedicamentoID", "Cantidad", "StockMinimo"])
    alto_riesgo = 0
    if len(farm):
        cons = farm.groupby("MedicamentoID", as_index=False).agg(
            consumo=("Cantidad", "sum"),
            stock_min=("StockMinimo", "first"),
            nombre=("Medicamento", "first"),
        )
        alto_riesgo = int((cons["consumo"] > cons["stock_min"] * 0.5).sum())

    costo_total = float(d["CostoTotalBs"].sum())

    return KPIBundle(
        tiempo_espera_promedio_min=round(tiempo_prom, 2),
        tiempo_espera_meta_min=120.0,
        pct_referencias_exitosas=round(pct_ref_ok, 2),
        pct_meta_referencias=95.0,
        ocupacion_camas_estimada_pct=round(ocup, 2),
        ocupacion_meta_pct=80.0,
        medicamentos_alto_riesgo=alto_riesgo,
        costo_total_periodo_bs=round(costo_total, 2),
        total_eventos=total,
    )
