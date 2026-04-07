# Sistema BI — Salud Pública Bolivia (ODS 3)

Aplicación en **Python** que consume la base **SQL Server** `BI_SaludPublica_Bolivia` (capa **Bronze**), aplica **limpieza tipo Silver** y calcula **KPIs tipo Gold** alineados al proyecto de *Inteligencia de Negocios* (referencias, tiempos de espera, epidemiología, ODS 3).

## Requisitos

- SQL Server con la base creada y poblada (`BI_SaludPublica_Bolivia_Bronze.sql` en la carpeta padre del proyecto).
- **Opcional y recomendado:** ejecutar también `BI_SaludPublica_Epidemiologia_Extension.sql` para cargar indicadores oficiales Bolivia 2024–2025 (dengue, tuberculosis, crónicos) y activar los gráficos por departamento con fuentes citadas.
- [Microsoft ODBC Driver for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) (17 u 18).
- Python 3.10+.

## Instalación

```powershell
cd "d:\inteligencia de negocios\base de datos de proyecto\sistema_bi_salud_publica"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

1. Copia `.env.example` a `.env`.
2. **`SQLSERVER_HOST`:** el mismo nombre que ves en el Explorador de objetos de SSMS (por ejemplo `Ale`, o `localhost\SQLEXPRESS` si usas Express).
3. **`SQLSERVER_PORT`:** déjalo vacío salvo que uses un puerto fijo conocido (1433). Con instancia con nombre, vacío suele funcionar mejor.
4. **Autenticación Windows** (SSMS muestra `ALE\Usuario` sin contraseña de SQL): pon `SQLSERVER_AUTH=windows` y deja `SQLSERVER_USER` y `SQLSERVER_PASSWORD` vacíos. No pongas tu usuario de Windows en `SQLSERVER_USER`.
5. Solo si usas login SQL (`sa`, etc.): `SQLSERVER_AUTH=sql` y usuario/contraseña reales de SQL Server.

## Ejecutar el dashboard

```powershell
streamlit run app.py
```

Se abrirá el navegador con las pestañas: KPIs, Epidemiología, Referencias, Calidad ETL y ODS 3.

## Estructura (materia BI)

| Capa   | Implementación |
|--------|------------------|
| Bronze | Consultas SQL en `etl/bronze_loader.py` |
| Silver | Limpieza en `etl/silver_transform.py` |
| Gold   | KPIs en `etl/gold_metrics.py` + gráficos en `app.py` |
