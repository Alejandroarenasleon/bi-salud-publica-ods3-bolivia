"""ETL: Bronze (SQL) → Silver (limpieza) → Gold (KPIs y agregados)."""

from .bronze_loader import load_eventos_hechos
from .gold_metrics import compute_kpis, indicadores_ods3_referencia
from .silver_transform import transform_eventos_silver

__all__ = [
    "load_eventos_hechos",
    "transform_eventos_silver",
    "compute_kpis",
    "indicadores_ods3_referencia",
]
