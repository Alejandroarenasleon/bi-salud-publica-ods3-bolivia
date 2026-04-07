"""Capa Bronze: extracción desde SQL Server (datos operacionales crudos)."""

from __future__ import annotations

import pandas as pd

from db import read_sql

QUERY_EVENTOS_HECHOS = """
SELECT
    e.EventoID,
    e.FechaEvento,
    e.TipoEvento,
    e.EnfermedadPrincipal,
    e.DiagnosticoSecundario,
    e.Cantidad,
    e.CostoTotalBs,
    e.TiempoEsperaMin,
    e.EstadoAtencion,
    e.CanalIngreso,
    e.Observaciones,
    ho.HospitalID AS HospitalOrigenID,
    ho.NombreHospital AS HospitalOrigen,
    ho.NivelAtencion AS NivelHospitalOrigen,
    ho.CamasHabilitadas AS CamasHospitalOrigen,
    g_o.Departamento AS DepartamentoOrigen,
    g_o.Ciudad AS CiudadOrigen,
    g_o.RegionSanitaria AS RegionOrigen,
    hd.NombreHospital AS HospitalDestino,
    g_d.Departamento AS DepartamentoDestino,
    p.PacienteID,
    p.Nombres AS PacienteNombres,
    p.Apellidos AS PacienteApellidos,
    p.Sexo,
    p.Seguro,
    m.MedicamentoID,
    m.NombreComercial AS Medicamento,
    m.Categoria AS CategoriaMedicamento,
    m.StockMinimo,
    m.CostoUnitarioBs AS PrecioUnitarioMedicamento
FROM bronze.EventosSalud e
INNER JOIN bronze.Hospitales ho ON e.HospitalOrigenID = ho.HospitalID
INNER JOIN bronze.Geografia g_o ON ho.GeografiaID = g_o.GeografiaID
LEFT JOIN bronze.Hospitales hd ON e.HospitalDestinoID = hd.HospitalID
LEFT JOIN bronze.Geografia g_d ON hd.GeografiaID = g_d.GeografiaID
LEFT JOIN bronze.Pacientes p ON e.PacienteID = p.PacienteID
LEFT JOIN bronze.Medicamentos m ON e.MedicamentoID = m.MedicamentoID
"""


QUERY_INDICADORES_EXTERNOS = """
SELECT
    IndicadorID,
    Anio,
    Departamento,
    GrupoEnfermedad,
    CasosReportados,
    Unidad,
    PeriodoReferencia,
    FuenteNombre,
    FuenteURL,
    Notas
FROM bronze.IndicadoresEpidemiologiaExterna
"""


def load_eventos_hechos() -> pd.DataFrame:
    return read_sql(QUERY_EVENTOS_HECHOS)


def load_indicadores_epidemiologia_externa() -> pd.DataFrame:
    """Indicadores públicos 2024–2025 (tabla extensión). Si no existe la tabla, DataFrame vacío."""
    try:
        return read_sql(QUERY_INDICADORES_EXTERNOS)
    except Exception:
        return pd.DataFrame()
