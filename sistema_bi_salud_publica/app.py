"""
Sistema de Inteligencia de Negocios — Salud Pública (ODS 3)
Dashboard: filtros laterales aplican a KPIs, gráficos operativos, ETL y contexto ODS.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from etl.bronze_loader import load_eventos_hechos, load_indicadores_epidemiologia_externa
from etl.gold_metrics import compute_kpis, indicadores_ods3_referencia
from etl.silver_transform import transform_eventos_silver
from etl.strategic_goals import recomendacion_sector, texto_objetivo


CHART_TEMPLATE = "plotly_dark"

st.set_page_config(
    page_title="BI Salud Pública Bolivia",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=120, show_spinner="Cargando capa Bronze (SQL Server)...")
def cached_bronze():
    return load_eventos_hechos()


@st.cache_data(ttl=120, show_spinner="Aplicando transformaciones Silver...")
def cached_silver():
    return transform_eventos_silver(cached_bronze())


@st.cache_data(ttl=300, show_spinner="Cargando indicadores epidemiológicos (tabla extensión)...")
def cached_externos():
    return load_indicadores_epidemiologia_externa()


def _fig_defaults(fig):
    fig.update_layout(template=CHART_TEMPLATE)
    return fig


def aplicar_filtros_operativos(
    df: pd.DataFrame,
    dept_sel: list[str],
    region_sel: list[str],
    texto_busqueda: str,
) -> pd.DataFrame:
    """Filtra eventos hospitalarios: departamento, región y texto libre (varias columnas)."""
    out = df.copy()
    if region_sel:
        out = out[out["RegionOrigen"].isin(region_sel)]
    if dept_sel:
        out = out[out["DepartamentoOrigen"].isin(dept_sel)]
    t = (texto_busqueda or "").strip()
    if t:
        ql = t.lower()

        def _has(series: pd.Series) -> pd.Series:
            return series.astype(str).str.lower().str.contains(ql, regex=False, na=False)

        m = (
            _has(out["EnfermedadPrincipal"])
            | _has(out["HospitalOrigen"])
            | _has(out["TipoEvento"])
        )
        for col in ("PacienteNombres", "PacienteApellidos", "CiudadOrigen", "DepartamentoOrigen", "Medicamento"):
            if col in out.columns:
                m |= _has(out[col])
        out = out[m]
    return out


def main() -> None:
    st.title("Estrategia de Inteligencia de Negocios en Salud Pública")
    st.caption(
        "ODS 3 — Índice de enfermedades por sector (departamento / región), decisiones de "
        "abastecimiento y tiempos de espera. Datos oficiales 2024–2025 + operación hospitalaria."
    )

    try:
        df_bronze = cached_bronze()
        df = cached_silver()
    except Exception as e:
        st.error("No se pudo conectar a SQL Server o leer los datos.")
        st.code(str(e), language="text")
        st.info(
            "Configura `.env` y ejecuta los scripts SQL en SSMS (base `BI_SaludPublica_Bolivia`)."
        )
        return

    df_ext = cached_externos()
    if df_ext.empty:
        st.warning(
            "No hay datos en `bronze.IndicadoresEpidemiologiaExterna`. "
            "Ejecuta en SSMS el archivo `BI_SaludPublica_Epidemiologia_Extension.sql`."
        )

    ods = indicadores_ods3_referencia()

    # --- Barra lateral ---
    with st.sidebar.expander("Cómo funcionan los filtros (léeme)", expanded=False):
        st.markdown(
            """
            | Control | Qué modifica |
            |--------|----------------|
            | **Objetivo** | Textos de recomendación y mensajes en Dashboard / ODS (enfoque logística vs tiempos). |
            | **Años** | Solo tabla y gráficos de **datos oficiales** (`IndicadoresEpidemiologiaExterna`). |
            | **Departamentos en foco** | Oficiales + eventos cuyo **departamento de origen** del hospital coincide. |
            | **Incluir Nacional** | Incluye filas con departamento *Nacional* (crónicos PAHO) en oficiales. |
            | **Región sanitaria** | Recorta eventos operativos por **región del hospital de origen**. |
            | **Buscar texto** | Filtra eventos donde aparezca el texto en diagnóstico, hospital, tipo de evento, paciente, ciudad, etc. |

            Los **KPIs** y gráficos **operativos** (Bronze/Silver) usan la combinación de departamento + región + búsqueda.
            """
        )

    st.sidebar.header("Decisión estratégica")
    _obj_labels = {
        "medicamentos": "Priorizar envío de medicamentos / insumos",
        "tiempo": "Recortar tiempo de espera",
        "integral": "Plan integral (ambos)",
    }
    objetivo = st.sidebar.radio(
        "Objetivo del tablero",
        options=list(_obj_labels.keys()),
        format_func=lambda k: _obj_labels[k],
        horizontal=False,
    )
    st.sidebar.markdown(texto_objetivo(objetivo))

    st.sidebar.header("Territorio y periodo")
    años_opts = sorted(df_ext["Anio"].dropna().unique().tolist()) if not df_ext.empty else [2024, 2025]
    años_sel = st.sidebar.multiselect("Años (datos oficiales)", options=años_opts, default=años_opts[-2:])
    dept_ext = sorted(df_ext["Departamento"].dropna().unique().tolist()) if not df_ext.empty else []
    dept_ops = sorted(set(dept_ext) | set(df["DepartamentoOrigen"].dropna().unique()))
    default_depts = [d for d in ["Santa Cruz", "La Paz", "Cochabamba", "Beni"] if d in dept_ops]
    if not default_depts:
        default_depts = dept_ops[:4] if len(dept_ops) >= 4 else dept_ops
    dept_sel = st.sidebar.multiselect(
        "Departamentos en foco (origen hospital)",
        options=dept_ops,
        default=default_depts,
        help="Filtra KPIs operativos, gráficos Bronze/Silver y datos oficiales por departamento.",
    )
    incluir_nacional = st.sidebar.checkbox(
        "Incluir fila Nacional (crónicos / prevalencias)",
        value=True,
        help="Hipertensión y diabetes a escala país suelen estar como 'Nacional'.",
    )

    region_sel = st.sidebar.multiselect(
        "Región sanitaria (hospital origen)",
        options=sorted(df["RegionOrigen"].dropna().unique()),
        default=[],
        help="Si eliges una o más regiones, solo cuentan eventos de hospitales en esa región.",
    )

    st.sidebar.header("Buscador (datos operativos)")
    buscar = st.sidebar.text_input(
        "Texto a buscar",
        value="",
        placeholder="Ej: dengue, Referencia, Japones, Mamani…",
        help="No distingue mayúsculas. Busca en diagnóstico, hospital, tipo evento, nombres, ciudad, medicamento.",
    )
    if buscar.strip():
        st.sidebar.success(f"Buscando: **{buscar.strip()}**")

    # Oficiales filtrados (años + dept + nacional)
    ext_f = df_ext.copy() if not df_ext.empty else pd.DataFrame()
    if not ext_f.empty and años_sel:
        ext_f = ext_f[ext_f["Anio"].isin(años_sel)]
    if not ext_f.empty:
        if dept_sel:
            cond_dept = ext_f["Departamento"].isin(dept_sel)
            if incluir_nacional:
                cond_dept = cond_dept | (ext_f["Departamento"] == "Nacional")
            ext_f = ext_f[cond_dept]
        elif not incluir_nacional:
            ext_f = ext_f[ext_f["Departamento"] != "Nacional"]

    # Operativo filtrado (dept + región + texto)
    df_filt = aplicar_filtros_operativos(df, dept_sel, region_sel, buscar)
    kpis = compute_kpis(df_filt)
    kpis_total = compute_kpis(df)

    evento_ids = set(df_filt["EventoID"].tolist()) if "EventoID" in df_filt.columns and len(df_filt) else set()
    if evento_ids:
        df_bronze_f = df_bronze[df_bronze["EventoID"].isin(evento_ids)]
        df_silver_f = df_filt
    else:
        df_bronze_f = df_bronze.iloc[0:0].copy()
        df_silver_f = df_filt

    st.sidebar.metric("Eventos operativos (filtrados)", f"{len(df_filt):,}", delta=f"de {len(df):,} totales")

    tab_dash, tab_epi, tab_ref, tab_sol, tab_etl, tab_ods = st.tabs(
        [
            "Dashboard KPIs",
            "Epidemiología",
            "Referencias y territorio",
            "Simulación de solución",
            "Calidad ETL (Silver)",
            "ODS 3 y CEPAL",
        ]
    )

    with tab_dash:
        st.caption(
            "Los **KPIs y gráficos de esta pestaña** usan los filtros: departamentos, región sanitaria y buscador."
        )
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Eventos (filtro actual)", f"{kpis.total_eventos:,}", help="Subconjunto según barra lateral")
        c2.metric(
            "Tiempo espera prom. (min)",
            f"{kpis.tiempo_espera_promedio_min:.1f}",
            delta=f"Meta ≤ {kpis.tiempo_espera_meta_min:.0f} min",
            delta_color="inverse",
        )
        c3.metric(
            "Referencias exitosas",
            f"{kpis.pct_referencias_exitosas:.1f}%",
            delta=f"Meta {kpis.pct_meta_referencias:.0f}%",
        )
        c4.metric(
            "Ocupación camas (estimada)",
            f"{kpis.ocupacion_camas_estimada_pct:.1f}%",
            delta=f"Meta ~{kpis.ocupacion_meta_pct:.0f}%",
        )
        c5.metric("Costo total filtrado (Bs)", f"{kpis.costo_total_periodo_bs:,.0f}")
        st.metric(
            "Medicamentos — alerta consumo vs stock (filtro actual)",
            kpis.medicamentos_alto_riesgo,
            help="Sobre el subconjunto filtrado de eventos.",
        )

        with st.expander("Comparar con totales sin filtro territorial/búsqueda"):
            st.write(
                f"**Total base:** {kpis_total.total_eventos:,} eventos | "
                f"Tiempo prom. {kpis_total.tiempo_espera_promedio_min:.1f} min | "
                f"Costo total {kpis_total.costo_total_periodo_bs:,.0f} Bs"
            )

        st.subheader("Relación objetivo ↔ indicadores")
        if objetivo == "medicamentos":
            st.success(
                "Enfoca: stock crítico y departamentos con mayor carga oficial "
                "(pestaña Epidemiología — datos externos + operativo filtrado)."
            )
        elif objetivo == "tiempo":
            st.success(
                "Enfoca: tiempo de espera y referencias en el **subconjunto filtrado** "
                "(ajusta departamento / región / búsqueda en la barra lateral)."
            )
        else:
            st.info("Vista combinada: abastecimiento + tiempos con los mismos filtros.")

        col_a, col_b = st.columns(2)
        with col_a:
            if len(df_filt):
                tipo_counts = df_filt["TipoEvento"].value_counts().reset_index()
                tipo_counts.columns = ["TipoEvento", "cantidad"]
                titulo_tipo = "Volumen por tipo de evento (filtrado)"
            else:
                tipo_counts = pd.DataFrame(columns=["TipoEvento", "cantidad"])
                titulo_tipo = "Sin datos con el filtro actual"
            fig_tipo = px.bar(
                tipo_counts,
                x="TipoEvento",
                y="cantidad",
                title=titulo_tipo,
                color="TipoEvento",
                template=CHART_TEMPLATE,
            )
            st.plotly_chart(fig_tipo, use_container_width=True)
        with col_b:
            tmp = df_filt.dropna(subset=["FechaEvento"]).copy()
            if len(tmp):
                tmp["periodo"] = tmp["FechaEvento"].dt.to_period("M").astype(str)
                mes = tmp.groupby("periodo", as_index=False).size().rename(columns={"size": "eventos"})
                titulo_mes = "Tendencia mensual (filtrado)"
            else:
                mes = pd.DataFrame(columns=["periodo", "eventos"])
                titulo_mes = "Sin fechas en el filtro actual"
            fig_mes = px.line(
                mes,
                x="periodo",
                y="eventos",
                markers=True,
                title=titulo_mes,
                template=CHART_TEMPLATE,
            )
            fig_mes.update_xaxes(tickangle=45)
            st.plotly_chart(fig_mes, use_container_width=True)

        if not ext_f.empty:
            st.subheader("Resumen oficial (mismos años / departamentos que en la barra)")
            mini = (
                ext_f.groupby("GrupoEnfermedad", as_index=False)["CasosReportados"]
                .sum()
                .sort_values("CasosReportados", ascending=False)
                .head(8)
            )
            fig_mini = px.bar(
                mini,
                x="GrupoEnfermedad",
                y="CasosReportados",
                title="Top cargas oficiales en selección actual",
                template=CHART_TEMPLATE,
            )
            fig_mini.update_xaxes(tickangle=45)
            st.plotly_chart(fig_mini, use_container_width=True)

    with tab_epi:
        st.caption(
            "Datos **oficiales** respetan años + departamentos + Nacional. "
            "Gráfico **operativo** usa además región y buscador."
        )
        st.subheader("Índice de enfermedades por sector (barras horizontales)")

        st.markdown("**Fuentes públicas** — `IndicadoresEpidemiologiaExterna`")
        if ext_f.empty:
            st.info("Sin filas tras filtros o tabla no cargada.")
        else:
            agg_pub = (
                ext_f.groupby("GrupoEnfermedad", as_index=False)["CasosReportados"]
                .sum()
                .sort_values("CasosReportados", ascending=True)
            )
            fig_pub = px.bar(
                agg_pub,
                x="CasosReportados",
                y="GrupoEnfermedad",
                orientation="h",
                title="Cargas notificadas / estimadas (filtros laterales)",
                labels={"CasosReportados": "Casos o magnitud", "GrupoEnfermedad": "Grupo / enfermedad"},
                template=CHART_TEMPLATE,
            )
            _fig_defaults(fig_pub)
            st.plotly_chart(fig_pub, use_container_width=True)

            with st.expander("Detalle y fuentes"):
                show_cols = [
                    "Anio",
                    "Departamento",
                    "GrupoEnfermedad",
                    "CasosReportados",
                    "Unidad",
                    "PeriodoReferencia",
                    "FuenteNombre",
                    "FuenteURL",
                ]
                avail = [c for c in show_cols if c in ext_f.columns]
                st.dataframe(ext_f[avail], use_container_width=True, hide_index=True)

        st.markdown("**Red hospitalaria (Bronze/Silver filtrado)**")
        df_op = df_filt.copy()
        if len(df_op):
            top_op = df_op["EnfermedadPrincipal"].value_counts().head(15).reset_index()
            top_op.columns = ["Enfermedad", "casos"]
        else:
            top_op = pd.DataFrame(columns=["Enfermedad", "casos"])
        top_op = top_op.sort_values("casos", ascending=True)
        fig_op = px.bar(
            top_op,
            x="casos",
            y="Enfermedad",
            orientation="h",
            title="Diagnósticos en eventos clínicos (departamento + región + búsqueda)",
            template=CHART_TEMPLATE,
        )
        _fig_defaults(fig_op)
        st.plotly_chart(fig_op, use_container_width=True)

        if not ext_f.empty and dept_sel:
            sub = ext_f[ext_f["Departamento"].isin(dept_sel)].copy()
            if len(sub):
                per_dept = sub.loc[sub.groupby("Departamento")["CasosReportados"].idxmax()]
                best = per_dept.sort_values("CasosReportados", ascending=False).iloc[0]
                st.success(
                    recomendacion_sector(
                        objetivo,
                        str(best["Departamento"]),
                        str(best["GrupoEnfermedad"]),
                        float(best["CasosReportados"]),
                    )
                )

        reg = df_filt.groupby("RegionOrigen", dropna=False).size().reset_index(name="eventos")
        if len(reg):
            fig_reg = px.treemap(
                reg,
                path=["RegionOrigen"],
                values="eventos",
                title="Eventos por región (subconjunto filtrado)",
                template=CHART_TEMPLATE,
            )
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("Sin eventos para treemap con el filtro actual.")

    with tab_ref:
        st.caption("Pastel oficial según departamentos; referencias y hospitales usan el **filtro operativo** completo.")

        st.subheader("Distribución oficial por enfermedad (pastel)")
        if ext_f.empty:
            st.warning("Carga la extensión SQL para ver distribución oficial.")
        else:
            if dept_sel:
                pie_df = ext_f[
                    ext_f["Departamento"].isin(dept_sel) | (ext_f["Departamento"] == "Nacional")
                ].copy()
            else:
                pie_df = ext_f.copy()
            if not incluir_nacional:
                pie_df = pie_df[pie_df["Departamento"] != "Nacional"]
            pie_agg = (
                pie_df.groupby("GrupoEnfermedad", as_index=False)["CasosReportados"]
                .sum()
                .query("CasosReportados > 0")
            )
            if pie_agg.empty:
                st.info("Sin datos para los departamentos seleccionados.")
            else:
                fig_pie = px.pie(
                    pie_agg,
                    names="GrupoEnfermedad",
                    values="CasosReportados",
                    title="Cargas oficiales en foco territorial",
                    template=CHART_TEMPLATE,
                    hole=0.15,
                )
                fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig_pie, use_container_width=True)
                st.dataframe(
                    pie_agg.sort_values("CasosReportados", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )

        st.subheader("Referencias (operativo filtrado)")
        ref = df_filt[df_filt["TipoEvento"] == "Referencia"].copy()
        if len(ref):
            est = ref["EstadoAtencion"].value_counts().reset_index()
            est.columns = ["Estado", "cantidad"]
            fig_est = px.pie(
                est,
                names="Estado",
                values="cantidad",
                title="Estado de referencias (filtro actual)",
                template=CHART_TEMPLATE,
            )
            st.plotly_chart(fig_est, use_container_width=True)

            dest = ref["DepartamentoDestino"].fillna("Sin destino").value_counts().head(12).reset_index()
            dest.columns = ["Departamento destino", "referencias"]
            fig_dest = px.bar(
                dest,
                x="Departamento destino",
                y="referencias",
                title="Referencias por destino (filtrado)",
                template=CHART_TEMPLATE,
            )
            st.plotly_chart(fig_dest, use_container_width=True)
        else:
            st.info("No hay referencias con el filtro actual (o ningún evento tras filtros).")

        st.subheader("Hospitales de origen (filtrado)")
        ho = (
            df_filt.groupby(["HospitalOrigen", "NivelHospitalOrigen"], dropna=False)
            .size()
            .reset_index(name="eventos")
            .sort_values("eventos", ascending=False)
        )
        if len(ho):
            fig_ho = px.bar(
                ho.head(15),
                x="eventos",
                y="HospitalOrigen",
                orientation="h",
                color="NivelHospitalOrigen",
                title="Top hospitales — subconjunto filtrado",
                template=CHART_TEMPLATE,
            )
            st.plotly_chart(fig_ho, use_container_width=True)
        else:
            st.info("Sin hospitales que mostrar con el filtro actual.")

    with tab_sol:
        st.caption(
            "Escenario prospectivo: proyecta cómo se verían las métricas si se aplican acciones "
            "de abastecimiento y/o eficiencia operativa en el periodo actual."
        )
        st.subheader("Plan de intervención y proyección")

        if len(df_filt) == 0 and ext_f.empty:
            st.info("No hay datos suficientes con los filtros actuales para simular.")
        else:
            c_plan1, c_plan2, c_plan3 = st.columns(3)
            with c_plan1:
                plan_abasto = st.checkbox(
                    "Aplicar plan abastecimiento (medicamentos)",
                    value=objetivo in ("medicamentos", "integral"),
                )
                red_casos = st.slider(
                    "Reducción esperada de casos críticos (%)",
                    min_value=0,
                    max_value=40,
                    value=15 if objetivo == "medicamentos" else 10,
                    step=1,
                    help="Impacta sobre cargas oficiales por enfermedad/departamento.",
                )
            with c_plan2:
                plan_tiempo = st.checkbox(
                    "Aplicar plan operativo (tiempo de espera)",
                    value=objetivo in ("tiempo", "integral"),
                )
                red_espera = st.slider(
                    "Reducción esperada en tiempo de espera (%)",
                    min_value=0,
                    max_value=50,
                    value=20 if objetivo == "tiempo" else 15,
                    step=1,
                    help="Impacta sobre tiempos operativos del subconjunto filtrado.",
                )
            with c_plan3:
                red_ref_fallida = st.slider(
                    "Reducción de referencias no atendidas (%)",
                    min_value=0,
                    max_value=50,
                    value=18,
                    step=1,
                    help="Reduce Pendiente/Derivado/Suspendido en escenario proyectado.",
                )

            if not ext_f.empty:
                st.markdown("**Proyección de cargas por enfermedad (oficiales filtradas)**")
                base_cargas = (
                    ext_f.groupby("GrupoEnfermedad", as_index=False)["CasosReportados"]
                    .sum()
                    .sort_values("CasosReportados", ascending=False)
                )
                sim_cargas = base_cargas.copy()
                factor_casos = (1 - red_casos / 100.0) if plan_abasto else 1.0
                sim_cargas["CasosProyectados"] = (sim_cargas["CasosReportados"] * factor_casos).round(0).astype(int)

                comp_cargas = pd.concat(
                    [
                        base_cargas.assign(Escenario="Actual").rename(columns={"CasosReportados": "Casos"}),
                        sim_cargas.assign(Escenario="Con solución").rename(columns={"CasosProyectados": "Casos"})[
                            ["GrupoEnfermedad", "Casos", "Escenario"]
                        ],
                    ],
                    ignore_index=True,
                )
                fig_sol_cargas = px.bar(
                    comp_cargas,
                    x="GrupoEnfermedad",
                    y="Casos",
                    color="Escenario",
                    barmode="group",
                    title="Actual vs proyectado por enfermedad",
                    template=CHART_TEMPLATE,
                )
                fig_sol_cargas.update_xaxes(tickangle=40)
                st.plotly_chart(fig_sol_cargas, use_container_width=True)

                delta_total = int(sim_cargas["CasosProyectados"].sum() - base_cargas["CasosReportados"].sum())
                st.metric(
                    "Variación neta de cargas (escenario proyectado)",
                    f"{delta_total:,}",
                    delta=f"{delta_total:,} casos/personas",
                    delta_color="inverse",
                )

            if len(df_filt):
                st.markdown("**Proyección operativa de tiempos y referencias (datos filtrados)**")
                espera_actual = float(df_filt["TiempoEsperaMin"].dropna().mean()) if len(df_filt["TiempoEsperaMin"].dropna()) else 0.0
                espera_proy = espera_actual * ((1 - red_espera / 100.0) if plan_tiempo else 1.0)
                c_ope1, c_ope2 = st.columns(2)
                c_ope1.metric("Tiempo espera actual (min)", f"{espera_actual:.1f}")
                c_ope2.metric(
                    "Tiempo espera proyectado (min)",
                    f"{espera_proy:.1f}",
                    delta=f"-{(espera_actual - espera_proy):.1f} min",
                    delta_color="inverse",
                )

                ref_act = df_filt[df_filt["TipoEvento"] == "Referencia"].copy()
                if len(ref_act):
                    est_act = ref_act["EstadoAtencion"].value_counts().to_dict()
                    est_proj = est_act.copy()
                    no_ok = ["Pendiente", "Derivado", "Suspendido"]
                    for s in no_ok:
                        v = int(est_proj.get(s, 0))
                        est_proj[s] = int(round(v * (1 - red_ref_fallida / 100.0), 0))
                    # lo recuperado se mueve a Atendido
                    reduc = sum(est_act.get(s, 0) - est_proj.get(s, 0) for s in no_ok)
                    est_proj["Atendido"] = int(est_proj.get("Atendido", 0) + reduc)

                    comp_ref = pd.DataFrame(
                        [
                            {"Estado": k, "Cantidad": v, "Escenario": "Actual"} for k, v in est_act.items()
                        ]
                        + [
                            {"Estado": k, "Cantidad": v, "Escenario": "Con solución"} for k, v in est_proj.items()
                        ]
                    )
                    fig_ref_sol = px.bar(
                        comp_ref,
                        x="Estado",
                        y="Cantidad",
                        color="Escenario",
                        barmode="group",
                        title="Estado de referencias: actual vs proyectado",
                        template=CHART_TEMPLATE,
                    )
                    st.plotly_chart(fig_ref_sol, use_container_width=True)

            st.subheader("Recomendación de plan")
            acciones = []
            if plan_abasto:
                acciones.append(
                    "- Abastecimiento focalizado en departamentos con mayor carga, control de stock mínimo y reposición semanal."
                )
            if plan_tiempo:
                acciones.append(
                    "- Reingeniería de flujo de referencia: triaje, agenda inteligente y derivación al primer hospital resolutivo."
                )
            if not acciones:
                acciones.append("- Activa al menos un plan para ver impacto proyectado.")
            st.markdown("\n".join(acciones))

    with tab_etl:
        st.caption(
            "Muestra solo filas cuyo **EventoID** sigue en el subconjunto filtrado (departamento + región + búsqueda)."
        )
        st.subheader("Capa Silver — comparación Bronze vs Silver")
        st.markdown(
            """
            - **Texto:** `strip()`, espacios múltiples, **Title Case** en nombres.
            - **Nulos:** columnas no críticas normalizadas.
            - **Filtro lateral:** reduce las filas mostradas a las mismas que alimentan KPIs y gráficos operativos.
            """
        )
        sample_cols = [
            "EventoID",
            "PacienteNombres",
            "PacienteApellidos",
            "EnfermedadPrincipal",
            "DiagnosticoSecundario",
            "CanalIngreso",
            "Observaciones",
            "DepartamentoOrigen",
            "RegionOrigen",
        ]
        avail_b = [c for c in sample_cols if c in df_bronze.columns]
        avail_s = [c for c in sample_cols if c in df.columns]
        n = st.slider("Máx. filas de muestra", 5, 100, 20)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Bronze (crudo)** — {len(df_bronze_f):,} filas con filtro")
            if len(df_bronze_f):
                st.dataframe(df_bronze_f[avail_b].head(n), use_container_width=True, hide_index=True)
            else:
                st.warning("Ninguna fila coincide con el filtro (prueba quitar búsqueda o ampliar departamentos).")
        with c2:
            st.markdown(f"**Silver (limpio)** — {len(df_silver_f):,} filas con filtro")
            if len(df_silver_f):
                st.dataframe(df_silver_f[avail_s].head(n), use_container_width=True, hide_index=True)
            else:
                st.warning("Sin datos filtrados en Silver.")

        cols_null = [c for c in sample_cols if c in df_bronze.columns and c in df.columns and c != "EventoID"]
        if cols_null and len(df_bronze_f) and len(df_silver_f):
            null_b = df_bronze_f[cols_null].isna().mean() * 100
            null_s = df_silver_f[cols_null].isna().mean() * 100
            comp = pd.DataFrame({"pct_null_bronze": null_b, "pct_null_silver": null_s})
            st.caption("% de nulos solo en subconjunto filtrado")
            st.dataframe(comp.round(2), use_container_width=True)

    with tab_ods:
        st.caption(
            "Indicadores ODS fijos del PDF + **puente** con tu selección oficial (crónicos / dengue / TB) según el objetivo."
        )
        st.subheader("Comparativo mortalidad materna (referencia CEPAL / PAHO)")
        st.markdown(
            f"**Indicador:** {ods['ods']} — contexto para mortalidad evitable y brecha regional."
        )
        fig_ods = go.Figure(
            data=[
                go.Bar(
                    name="MMR por 100 mil nacidos vivos",
                    x=["Bolivia 2020 (PAHO)", "Bolivia ~2023 (est.)", "Promedio regional"],
                    y=[ods["mmr_bolivia_2020"], ods["mmr_bolivia_est_2023"], ods["mmr_regional_promedio"]],
                )
            ]
        )
        fig_ods.update_layout(template=CHART_TEMPLATE, yaxis_title="MMR", title="Razón de mortalidad materna")
        st.plotly_chart(fig_ods, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("Mortalidad infantil 2022 (por 1.000)", f"{ods['mortalidad_infantil_2022']}")
        c2.metric("Meta reducción mortalidad evitable (PDF)", f"{ods['meta_reduccion_mortalidad_evitable_pct']}%")

        st.subheader("Tu selección oficial ↔ objetivo estratégico")
        if ext_f.empty:
            st.info("Sin datos oficiales filtrados (revisa años y departamentos en la barra lateral).")
        else:
            cronicos = ext_f[
                ext_f["GrupoEnfermedad"].astype(str).str.contains(
                    "Diabetes|Hipertensión|hipertension|mellitus",
                    case=False,
                    regex=True,
                    na=False,
                )
            ]
            infecto = ext_f[
                ext_f["GrupoEnfermedad"].astype(str).str.contains("Dengue|Tuberculosis", case=False, regex=True, na=False)
            ]
            c_a, c_b = st.columns(2)
            with c_a:
                st.metric("Suma cargas crónicos (selección)", f"{int(cronicos['CasosReportados'].sum()):,}" if len(cronicos) else "0")
            with c_b:
                st.metric("Suma dengue+TB (selección)", f"{int(infecto['CasosReportados'].sum()):,}" if len(infecto) else "0")

            if objetivo == "medicamentos":
                st.success(
                    "Objetivo **medicamentos**: la ODS 3 se apoya en continuidad de tratamiento; prioriza insumos "
                    "para grupos de mayor magnitud en tu tabla (crónicos + alertas de stock en Dashboard)."
                )
            elif objetivo == "tiempo":
                st.success(
                    "Objetivo **tiempo de espera**: reduce demoras en derivaciones y seguimiento de crónicos; "
                    "cruza con referencias filtradas en la pestaña anterior."
                )
            else:
                st.info("Objetivo **integral**: combina abastecimiento y flujo asistencial en los mismos departamentos.")

            resumen = (
                ext_f.groupby(["Departamento", "GrupoEnfermedad"], as_index=False)["CasosReportados"]
                .sum()
                .sort_values("CasosReportados", ascending=False)
                .head(15)
            )
            st.markdown("**Top 15 filas (departamento × enfermedad) con filtros actuales**")
            st.dataframe(resumen, use_container_width=True, hide_index=True)

            if len(resumen):
                fig_ctx = px.bar(
                    resumen,
                    x="CasosReportados",
                    y="GrupoEnfermedad",
                    orientation="h",
                    color="Departamento",
                    title="Contexto ODS: cargas oficiales en tu selección",
                    template=CHART_TEMPLATE,
                )
                st.plotly_chart(fig_ctx, use_container_width=True)

    st.divider()
    st.caption(
        "Filtros laterales: oficiales (años + dept + Nacional) y operativos (dept + región + búsqueda). "
        "Métrica ‘Eventos filtrados’ resume el subconjunto activo."
    )


if __name__ == "__main__":
    main()
