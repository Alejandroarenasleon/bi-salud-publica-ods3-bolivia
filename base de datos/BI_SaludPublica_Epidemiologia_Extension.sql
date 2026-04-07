/*
   Extensión BI Salud Pública — Indicadores epidemiológicos Bolivia (referencia pública 2024–2025)
   Ejecutar en SSMS sobre la base: BI_SaludPublica_Bolivia
   Fuentes resumidas en FuenteNombre / FuenteURL (validación académica en los enlaces).
*/

USE BI_SaludPublica_Bolivia;
GO

IF OBJECT_ID('bronze.IndicadoresEpidemiologiaExterna', 'U') IS NOT NULL
    DROP TABLE bronze.IndicadoresEpidemiologiaExterna;
GO

CREATE TABLE bronze.IndicadoresEpidemiologiaExterna
(
    IndicadorID       INT IDENTITY(1,1) PRIMARY KEY,
    Anio              INT NOT NULL,
    Departamento      NVARCHAR(60) NOT NULL,
    GrupoEnfermedad   NVARCHAR(120) NOT NULL,
    CasosReportados   INT NOT NULL,
    Unidad            NVARCHAR(40) NOT NULL CONSTRAINT DF_Epi_Unidad DEFAULT (N'casos notificados'),
    PeriodoReferencia NVARCHAR(80) NULL,
    FuenteNombre      NVARCHAR(220) NOT NULL,
    FuenteURL         NVARCHAR(600) NULL,
    Notas             NVARCHAR(800) NULL,
    CONSTRAINT CHK_Epi_Casos CHECK (CasosReportados >= 0)
);
GO

CREATE INDEX IX_Epi_Dept_Anio ON bronze.IndicadoresEpidemiologiaExterna (Departamento, Anio);
GO

/* ---- Dengue: corte febrero 2024 (casos confirmados por departamento) — MinSalud ---- */
INSERT INTO bronze.IndicadoresEpidemiologiaExterna
(Anio, Departamento, GrupoEnfermedad, CasosReportados, PeriodoReferencia, FuenteNombre, FuenteURL, Notas)
VALUES
(2024, N'Santa Cruz', N'Dengue', 2602, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', N'Boletín nacional; departamento con mayor carga en ese corte.'),
(2024, N'Beni', N'Dengue', 569, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', NULL),
(2024, N'Chuquisaca', N'Dengue', 239, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', NULL),
(2024, N'Pando', N'Dengue', 289, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', NULL),
(2024, N'Tarija', N'Dengue', 166, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', NULL),
(2024, N'Cochabamba', N'Dengue', 236, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', NULL),
(2024, N'La Paz', N'Dengue', 126, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', NULL),
(2024, N'Oruro', N'Dengue', 10, N'Hasta 09-feb-2024', N'Ministerio de Salud y Deportes', N'https://www.minsalud.gob.bo/3929-ministerio-de-salud-reporta-4-227-casos-confirmados-de-dengue-en-el-pais-hasta-el-9-de-febrero', N'Cifra baja en boletín (sospechosos predominan en otros departamentos).');

/* ---- Dengue 2025: total nacional referido en atlas/visualización epidemiológica; reparto proporcional por patrón 2024 ----
   Total aproximado país ~38.028 casos e incidencia 302,7/100.000 (fuente atlas/visual 2025). */
DECLARE @tot2025 INT = 38028;
DECLARE @sum2024 INT = (SELECT SUM(CasosReportados) FROM bronze.IndicadoresEpidemiologiaExterna WHERE Anio = 2024 AND GrupoEnfermedad = N'Dengue');
INSERT INTO bronze.IndicadoresEpidemiologiaExterna (Anio, Departamento, GrupoEnfermedad, CasosReportados, PeriodoReferencia, FuenteNombre, FuenteURL, Notas)
SELECT
    2025,
    Departamento,
    N'Dengue',
    CAST(ROUND(1.0 * CasosReportados / @sum2024 * @tot2025, 0) AS INT),
    N'Estimación 2025 (reparto proporcional corte 2024)',
    N'Consolidado visual / prensa nacional (total país referido)',
    N'https://denguevisualatlas.com/paises/bolivia/',
    N'Cálculo académico: total nacional publicado distribuido según pesos del corte MinSalud feb-2024.'
FROM bronze.IndicadoresEpidemiologiaExterna
WHERE Anio = 2024 AND GrupoEnfermedad = N'Dengue';

/* ---- Tuberculosis: Santa Cruz ~5.068 (2024); reparto resto aproximado prensa/MinSalud ---- */
INSERT INTO bronze.IndicadoresEpidemiologiaExterna (Anio, Departamento, GrupoEnfermedad, CasosReportados, PeriodoReferencia, FuenteNombre, FuenteURL, Notas)
VALUES
(2024, N'Santa Cruz', N'Tuberculosis', 5068, N'Año 2024', N'El Deber / notificación regional', N'https://eldeber.com.bo/pais/tuberculosis-bolivia-bajan-los-casos-pero-santa-cruz-concentra-casi-la-mitad_1774368218', N'Departamento con mayor carga; ~47–50% del país en varias series.'),
(2024, N'La Paz', N'Tuberculosis', 1900, N'Año 2024 (estimado)', N'MinSalud / agregados nacionales (~9–10 mil casos)', N'https://www.minsalud.gob.bo/6572-salud-bolivia-ocupa-el-octavo-puesto-de-mayor-carga-de-tuberculosis-de-la-region-empero-redujo-su-incidencia', N'Estimación departamental para tablero (no sustituye boletín oficial departamental).'),
(2024, N'Cochabamba', N'Tuberculosis', 1600, N'Año 2024 (estimado)', N'MinSalud / agregados nacionales', N'https://www.minsalud.gob.bo/6572-salud-bolivia-ocupa-el-octavo-puesto-de-mayor-carga-de-tuberculosis-de-la-region-empero-redujo-su-incidencia', NULL),
(2024, N'Oruro', N'Tuberculosis', 350, N'Año 2024 (estimado)', N'Distribución residual modelo', NULL, N'Valor ilustrativo para análisis territorial.'),
(2024, N'Chuquisaca', N'Tuberculosis', 280, N'Año 2024 (estimado)', N'Distribución residual modelo', NULL, NULL),
(2024, N'Tarija', N'Tuberculosis', 220, N'Año 2024 (estimado)', N'Distribución residual modelo', NULL, NULL),
(2024, N'Beni', N'Tuberculosis', 180, N'Año 2024 (estimado)', N'Distribución residual modelo', NULL, NULL),
(2024, N'Potosi', N'Tuberculosis', 200, N'Año 2024 (estimado)', N'Distribución residual modelo', NULL, NULL),
(2024, N'Pando', N'Tuberculosis', 34, N'Corte 2024 (referido prensa)', N'El Día / reportes regionales', N'https://eldia.com.bo/2025-03-24/santa-cruz/santa-cruz-el-departamento-mas-afectado-por-la-tuberculosis-con-mas-de-4500-casos-por-ano.html', N'Orden de magnitud bajo frente a eje Santa Cruz–La Paz–Cochabamba.');

/* TB 2025: ligera reducción nacional tendencial — factor 0.95 sobre 2024 dept */
INSERT INTO bronze.IndicadoresEpidemiologiaExterna (Anio, Departamento, GrupoEnfermedad, CasosReportados, PeriodoReferencia, FuenteNombre, FuenteURL, Notas)
SELECT
    2025,
    src.Departamento,
    N'Tuberculosis',
    CAST(ROUND(src.CasosReportados * 0.95, 0) AS INT),
    N'Proyección 2025 (–5% vs 2024)',
    N'Modelo tablero BI',
    NULL,
    N'Proyección pedagógica; contrastar con SNIS-VE/SEDES.'
FROM bronze.IndicadoresEpidemiologiaExterna AS src
WHERE src.Anio = 2024
  AND src.GrupoEnfermedad = N'Tuberculosis';

/* ---- Diabetes / hipertensión: cargas crónicas (orden de magnitud nacional PAHO/perfil país) ---- */
INSERT INTO bronze.IndicadoresEpidemiologiaExterna (Anio, Departamento, GrupoEnfermedad, CasosReportados, Unidad, PeriodoReferencia, FuenteNombre, FuenteURL, Notas)
VALUES
(2024, N'Nacional', N'Diabetes mellitus (prevalencia aproximada)', 420000, N'personas (orden de magnitud)', N'Perfil país / crónicos', N'PAHO — Perfil de país Bolivia', N'https://hia.paho.org/es/perfiles-de-pais/bolivia', N'No es conteo anual de casos nuevos; sirve para priorizar abastecimiento de insulina y metformina.'),
(2025, N'Nacional', N'Diabetes mellitus (prevalencia aproximada)', 430000, N'personas (orden de magnitud)', N'Proyección 2025', N'Perfil país PAHO (tendencia)', N'https://hia.paho.org/es/perfiles-de-pais/bolivia', N'Valor ilustrativo para decisión logística.'),
(2024, N'Nacional', N'Hipertensión arterial (carga estimada)', 1800000, N'personas (orden de magnitud)', N'Encuestas y perfil regional', N'PAHO — Perfil de país Bolivia', N'https://hia.paho.org/es/perfiles-de-pais/bolivia', N'Prioriza continuidad de tratamiento y tiempo de espera en crónicos.'),
(2024, N'Santa Cruz', N'Diabetes mellitus (casos nuevos notificados - orden magnitud)', 3200, N'casos nuevos (estimado dept)', N'Modelo departamental SNIS (ilustrativo)', N'Modelo tablero BI / estimación departamental', NULL, N'Reparto aproximado para comparar con dengue/TB en el mismo departamento.'),
(2024, N'La Paz', N'Diabetes mellitus (casos nuevos notificados - orden magnitud)', 2800, N'casos nuevos (estimado dept)', N'Modelo departamental SNIS (ilustrativo)', N'Modelo tablero BI / estimación departamental', NULL, NULL),
(2024, N'Cochabamba', N'Diabetes mellitus (casos nuevos notificados - orden magnitud)', 2100, N'casos nuevos (estimado dept)', N'Modelo departamental SNIS (ilustrativo)', N'Modelo tablero BI / estimación departamental', NULL, NULL);

GO

SELECT Anio, Departamento, GrupoEnfermedad, CasosReportados, FuenteNombre
FROM bronze.IndicadoresEpidemiologiaExterna
ORDER BY Anio, Departamento, GrupoEnfermedad;
GO
