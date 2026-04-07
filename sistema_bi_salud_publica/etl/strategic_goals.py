"""Objetivos estratégicos según el tablero (logística vs tiempos de espera)."""

from __future__ import annotations


def texto_objetivo(codigo: str) -> str:
    m = {
        "medicamentos": (
            "Priorizar abastecimiento de medicamentos e insumos (quimioterapia, antibióticos, "
            "insulina, antihipertensivos) hacia los departamentos con mayor carga notificada."
        ),
        "tiempo": (
            "Reducir el tiempo de espera en referencias y consulta de crónicos mediante "
            "triaje, agenda y descongestión de hospitales de referencia."
        ),
        "integral": (
            "Combinar envío focalizado de fármacos y medidas operativas para acortar esperas "
            "en los ejes con mayor incidencia (dengue/TB/diabetes según sector)."
        ),
    }
    return m.get(codigo, m["integral"])


def recomendacion_sector(
    objetivo: str,
    departamento_top: str,
    enfermedad_top: str,
    casos: float,
) -> str:
    base = (
        f"En **{departamento_top}**, la carga más visible es **{enfermedad_top}** "
        f"(orden de magnitud **{casos:,.0f}** casos/personas según fuente seleccionada)."
    )
    if objetivo == "medicamentos":
        return base + (
            " → Acción sugerida: reforzar stock y cadena de frío, pedidos SEDES/MinSalud "
            "y alertas a farmacia hospitalaria."
        )
    if objetivo == "tiempo":
        return base + (
            " → Acción sugerida: priorizar turnos, telemedicina de seguimiento y flujo de referencias "
            "hacia el hospital correcto en la primera derivación."
        )
    return base + (
        " → Acción sugerida: plan mixto (abastecimiento + reorganización de demanda) con seguimiento mensual."
    )
