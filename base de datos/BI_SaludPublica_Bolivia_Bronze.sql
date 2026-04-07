/* ============================================================
   PROYECTO BI EN SALUD PUBLICA (ODS 3) - CAPA BRONZE
   SQL Server / T-SQL - Script completo (DDL + DML)
   ============================================================ */

-- 1) Crear base de datos
IF DB_ID('BI_SaludPublica_Bolivia') IS NOT NULL
BEGIN
    ALTER DATABASE BI_SaludPublica_Bolivia SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE BI_SaludPublica_Bolivia;
END;
GO

CREATE DATABASE BI_SaludPublica_Bolivia;
GO

USE BI_SaludPublica_Bolivia;
GO

CREATE SCHEMA bronze;
GO

/* ============================================================
   2) TABLAS MAESTRAS / DIMENSIONES
   ============================================================ */

-- Geografia (Bolivia)
CREATE TABLE bronze.Geografia
(
    GeografiaID       INT IDENTITY(1,1) PRIMARY KEY,
    Departamento      NVARCHAR(50) NOT NULL,
    Ciudad            NVARCHAR(80) NOT NULL,
    RegionSanitaria   NVARCHAR(30) NOT NULL, -- Altiplano, Valles, Llanos, Chaco, Amazonia
    CONSTRAINT UQ_Geografia_Departamento_Ciudad UNIQUE (Departamento, Ciudad)
);
GO

-- Hospitales
CREATE TABLE bronze.Hospitales
(
    HospitalID            INT IDENTITY(1,1) PRIMARY KEY,
    NombreHospital        NVARCHAR(120) NOT NULL,
    GeografiaID           INT NOT NULL,
    NivelAtencion         VARCHAR(20) NOT NULL, -- 1er, 2do, 3er nivel
    TipoGestion           VARCHAR(20) NOT NULL, -- Publico, CNS, Universitario
    CamasHabilitadas      INT NOT NULL,
    EspecialidadPrincipal NVARCHAR(80) NULL,
    CONSTRAINT FK_Hospitales_Geografia FOREIGN KEY (GeografiaID) REFERENCES bronze.Geografia(GeografiaID),
    CONSTRAINT CHK_Hospitales_Nivel CHECK (NivelAtencion IN ('1er Nivel','2do Nivel','3er Nivel')),
    CONSTRAINT CHK_Hospitales_Tipo CHECK (TipoGestion IN ('Publico','CNS','Universitario')),
    CONSTRAINT CHK_Hospitales_Camas CHECK (CamasHabilitadas > 0)
);
GO

-- Pacientes
CREATE TABLE bronze.Pacientes
(
    PacienteID              INT IDENTITY(1,1) PRIMARY KEY,
    Nombres                 NVARCHAR(100) NOT NULL,
    Apellidos               NVARCHAR(100) NOT NULL,
    Sexo                    CHAR(1) NOT NULL,
    FechaNacimiento         DATE NOT NULL,
    GeografiaResidenciaID   INT NOT NULL,
    Telefono                VARCHAR(20) NULL,      -- no critica (puede venir sucia)
    Correo                  NVARCHAR(120) NULL,    -- no critica
    FechaRegistro           DATE NOT NULL,
    Seguro                  VARCHAR(30) NOT NULL,
    CONSTRAINT FK_Pacientes_Geografia FOREIGN KEY (GeografiaResidenciaID) REFERENCES bronze.Geografia(GeografiaID),
    CONSTRAINT CHK_Pacientes_Sexo CHECK (Sexo IN ('F','M')),
    CONSTRAINT CHK_Pacientes_Seguro CHECK (Seguro IN ('SUS','CNS','Privado','Ninguno')),
    CONSTRAINT CHK_Pacientes_Edad CHECK (FechaNacimiento <= DATEADD(YEAR, -1, CAST(GETDATE() AS DATE)))
);
GO

-- Empleados de salud
CREATE TABLE bronze.EmpleadosSalud
(
    EmpleadoID              INT IDENTITY(1,1) PRIMARY KEY,
    Nombres                 NVARCHAR(100) NOT NULL,
    Apellidos               NVARCHAR(100) NOT NULL,
    Cargo                   VARCHAR(40) NOT NULL,
    Especialidad            NVARCHAR(80) NULL,
    HospitalID              INT NOT NULL,
    FechaIngreso            DATE NOT NULL,
    Turno                   VARCHAR(20) NOT NULL,
    CorreoInstitucional     NVARCHAR(120) NULL, -- no critica
    CONSTRAINT FK_Empleados_Hospitales FOREIGN KEY (HospitalID) REFERENCES bronze.Hospitales(HospitalID),
    CONSTRAINT CHK_Empleados_Cargo CHECK (Cargo IN ('Medico','Enfermeria','Bioquimica','Farmacia','Administrativo','Epidemiologia')),
    CONSTRAINT CHK_Empleados_Turno CHECK (Turno IN ('Manana','Tarde','Noche','Rotativo'))
);
GO

-- Medicamentos e insumos (stock critico)
CREATE TABLE bronze.Medicamentos
(
    MedicamentoID          INT IDENTITY(1,1) PRIMARY KEY,
    NombreComercial        NVARCHAR(120) NOT NULL,
    Categoria              VARCHAR(40) NOT NULL,
    Presentacion           NVARCHAR(60) NOT NULL,
    CostoUnitarioBs        DECIMAL(10,2) NOT NULL,
    StockMinimo            INT NOT NULL,
    RequiereCadenaFrio     BIT NOT NULL DEFAULT 0,
    EstadoRegulatorio      VARCHAR(20) NOT NULL,
    CONSTRAINT CHK_Medicamentos_Costo CHECK (CostoUnitarioBs > 0),
    CONSTRAINT CHK_Medicamentos_StockMin CHECK (StockMinimo >= 0),
    CONSTRAINT CHK_Medicamentos_Estado CHECK (EstadoRegulatorio IN ('Vigente','EnRevision','Restringido'))
);
GO

/* ============================================================
   3) TABLA TRANSACCIONAL PRINCIPAL (HECHOS BRONZE)
   ============================================================ */

CREATE TABLE bronze.EventosSalud
(
    EventoID                 BIGINT IDENTITY(1,1) PRIMARY KEY,
    FechaEvento              DATETIME2(0) NOT NULL,
    TipoEvento               VARCHAR(20) NOT NULL, -- Consulta, Emergencia, Referencia, Hospitalizacion, Farmacia
    PacienteID               INT NOT NULL,
    HospitalOrigenID         INT NOT NULL,
    HospitalDestinoID        INT NULL,             -- no critico en consultas locales
    EmpleadoID               INT NOT NULL,
    MedicamentoID            INT NULL,             -- no todos los eventos usan medicamento
    EnfermedadPrincipal      NVARCHAR(80) NOT NULL,
    DiagnosticoSecundario    NVARCHAR(120) NULL,   -- columna no critica (reto limpieza)
    Cantidad                 INT NULL,
    CostoTotalBs             DECIMAL(12,2) NOT NULL,
    TiempoEsperaMin          INT NULL,
    EstadoAtencion           VARCHAR(20) NOT NULL,
    CanalIngreso             VARCHAR(20) NULL,     -- no critica
    Observaciones            NVARCHAR(250) NULL,   -- no critica (reto limpieza)
    FechaRegistroETL         DATETIME2(0) NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_Eventos_Paciente FOREIGN KEY (PacienteID) REFERENCES bronze.Pacientes(PacienteID),
    CONSTRAINT FK_Eventos_HospitalOrigen FOREIGN KEY (HospitalOrigenID) REFERENCES bronze.Hospitales(HospitalID),
    CONSTRAINT FK_Eventos_HospitalDestino FOREIGN KEY (HospitalDestinoID) REFERENCES bronze.Hospitales(HospitalID),
    CONSTRAINT FK_Eventos_Empleado FOREIGN KEY (EmpleadoID) REFERENCES bronze.EmpleadosSalud(EmpleadoID),
    CONSTRAINT FK_Eventos_Medicamento FOREIGN KEY (MedicamentoID) REFERENCES bronze.Medicamentos(MedicamentoID),

    CONSTRAINT CHK_Eventos_Tipo CHECK (TipoEvento IN ('Consulta','Emergencia','Referencia','Hospitalizacion','Farmacia')),
    CONSTRAINT CHK_Eventos_Estado CHECK (EstadoAtencion IN ('Atendido','Pendiente','Derivado','Suspendido')),
    CONSTRAINT CHK_Eventos_Cantidad CHECK (Cantidad IS NULL OR Cantidad >= 0),
    CONSTRAINT CHK_Eventos_Costo CHECK (CostoTotalBs >= 0),
    CONSTRAINT CHK_Eventos_Tiempo CHECK (TiempoEsperaMin IS NULL OR TiempoEsperaMin >= 0)
);
GO

/* ============================================================
   4) CARGA DE DATOS MAESTROS (>=15 POR TABLA)
   ============================================================ */

-- Geografia (20 registros)
INSERT INTO bronze.Geografia (Departamento, Ciudad, RegionSanitaria)
VALUES
('La Paz','La Paz','Altiplano'),
('La Paz','El Alto','Altiplano'),
('La Paz','Viacha','Altiplano'),
('Santa Cruz','Santa Cruz de la Sierra','Llanos'),
('Santa Cruz','Montero','Llanos'),
('Santa Cruz','Warnes','Llanos'),
('Cochabamba','Cochabamba','Valles'),
('Cochabamba','Sacaba','Valles'),
('Cochabamba','Quillacollo','Valles'),
('Tarija','Tarija','Chaco'),
('Tarija','Yacuiba','Chaco'),
('Oruro','Oruro','Altiplano'),
('Potosi','Potosi','Altiplano'),
('Chuquisaca','Sucre','Valles'),
('Beni','Trinidad','Amazonia'),
('Pando','Cobija','Amazonia'),
('Beni','Riberalta','Amazonia'),
('Chuquisaca','Monteagudo','Chaco'),
('Potosi','Uyuni','Altiplano'),
('Oruro','Challapata','Altiplano');
GO

-- Hospitales (15 registros)
INSERT INTO bronze.Hospitales (NombreHospital, GeografiaID, NivelAtencion, TipoGestion, CamasHabilitadas, EspecialidadPrincipal)
VALUES
('Hospital de la Mujer', 1, '3er Nivel', 'Publico', 240, 'Ginecologia y Obstetricia'),
('Hospital del Nino La Paz', 1, '3er Nivel', 'Publico', 180, 'Pediatria'),
('Hospital del Norte El Alto', 2, '3er Nivel', 'Publico', 220, 'Medicina Interna'),
('Hospital Japones', 4, '3er Nivel', 'Publico', 300, 'Traumatologia'),
('Hospital de Ninos Santa Cruz', 4, '3er Nivel', 'Publico', 190, 'Pediatria'),
('Hospital San Juan de Dios Tarija', 10, '2do Nivel', 'Publico', 140, 'Emergencias'),
('Hospital Viedma', 7, '3er Nivel', 'Publico', 260, 'Cirugia General'),
('Hospital Obrero CNS La Paz', 1, '3er Nivel', 'CNS', 280, 'Cardiologia'),
('Hospital Obrero CNS Santa Cruz', 4, '3er Nivel', 'CNS', 230, 'Medicina Interna'),
('Hospital Materno Infantil Cochabamba', 7, '2do Nivel', 'Publico', 150, 'Materno Infantil'),
('Hospital Daniel Bracamonte', 13, '2do Nivel', 'Publico', 130, 'Cirugia'),
('Hospital San Pedro Claver Sucre', 14, '2do Nivel', 'Universitario', 120, 'Medicina Interna'),
('Hospital Oruro Corea', 12, '2do Nivel', 'Publico', 125, 'Emergencias'),
('Hospital German Busch Trinidad', 15, '2do Nivel', 'Publico', 115, 'Infectologia'),
('Hospital Roberto Galindo Cobija', 16, '2do Nivel', 'Publico', 100, 'Medicina General');
GO

-- Pacientes (20 registros, con algunos nombres "sucios")
INSERT INTO bronze.Pacientes (Nombres, Apellidos, Sexo, FechaNacimiento, GeografiaResidenciaID, Telefono, Correo, FechaRegistro, Seguro)
VALUES
('Juan Carlos','Mamani Quispe','M','1990-06-10',2,'76543210','juan.mamani@mail.com',DATEADD(DAY,-680,CAST(GETDATE() AS DATE)),'SUS'),
('  maria jose ','Choque Apaza','F','1988-11-02',1,'73455122','maria.choque@mail.com',DATEADD(DAY,-510,CAST(GETDATE() AS DATE)),'SUS'),
('Luis Fernando','Rojas Flores','M','1979-01-15',4,'72111222','luis.rojas@mail.com',DATEADD(DAY,-430,CAST(GETDATE() AS DATE)),'CNS'),
('carla andrea','Guzman Paredes','F','1996-03-22',7,'79990011','carla.guzman@mail.com',DATEADD(DAY,-300,CAST(GETDATE() AS DATE)),'Privado'),
('Diego Alejandro','Vargas Nina','M','2001-12-01',10,'78812233','diego.vargas@mail.com',DATEADD(DAY,-280,CAST(GETDATE() AS DATE)),'SUS'),
('Roxana','Llanos Hurtado','F','1994-09-09',4,'71122334','roxana.llanos@mail.com',DATEADD(DAY,-220,CAST(GETDATE() AS DATE)),'SUS'),
('Miguel Angel','Torrez Cardenas','M','1985-04-17',12,'77776655','miguel.torrez@mail.com',DATEADD(DAY,-190,CAST(GETDATE() AS DATE)),'CNS'),
('Ana Lucia','Condori Huanca','F','1998-05-26',13,'74445566','ana.condori@mail.com',DATEADD(DAY,-170,CAST(GETDATE() AS DATE)),'SUS'),
('Jose Luis','Quisbert Mamani','M','1975-07-30',15,'73334455','jose.quisbert@mail.com',DATEADD(DAY,-155,CAST(GETDATE() AS DATE)),'Ninguno'),
('Patricia','Mendoza Soria','F','1982-10-19',14,'72223344','patricia.mendoza@mail.com',DATEADD(DAY,-140,CAST(GETDATE() AS DATE)),'SUS'),
(' Oscar ','Villarroel Arce','M','1993-08-08',5,'76667788','oscar.villarroel@mail.com',DATEADD(DAY,-120,CAST(GETDATE() AS DATE)),'Privado'),
('Yolanda','Poma Ticona','F','1987-02-13',3,'75556677','yolanda.poma@mail.com',DATEADD(DAY,-105,CAST(GETDATE() AS DATE)),'SUS'),
('Nicolas','Arias Duran','M','1999-01-09',8,'70001122','nicolas.arias@mail.com',DATEADD(DAY,-90,CAST(GETDATE() AS DATE)),'SUS'),
('beatriz','Sanchez Rocabado','F','1991-06-03',9,'78881100','beatriz.sanchez@mail.com',DATEADD(DAY,-80,CAST(GETDATE() AS DATE)),'CNS'),
('Marcelo','Aguilar Vera','M','1980-11-27',11,'74440022','marcelo.aguilar@mail.com',DATEADD(DAY,-70,CAST(GETDATE() AS DATE)),'SUS'),
('Gabriela','Arenas Leon','F','1997-12-15',10,'72224466','gabriela.arenas@mail.com',DATEADD(DAY,-62,CAST(GETDATE() AS DATE)),'SUS'),
('Rene','Flores Cruz','M','1983-03-05',6,'73335577','rene.flores@mail.com',DATEADD(DAY,-55,CAST(GETDATE() AS DATE)),'CNS'),
('Sofia','Mendez Loza','F','2000-04-01',16,'75553311','sofia.mendez@mail.com',DATEADD(DAY,-42,CAST(GETDATE() AS DATE)),'SUS'),
('Javier','Aliaga Salinas','M','1992-09-23',17,'74446699','javier.aliaga@mail.com',DATEADD(DAY,-30,CAST(GETDATE() AS DATE)),'Privado'),
('Daniela','Perez Gutierrez','F','1995-01-12',18,'71118844','daniela.perez@mail.com',DATEADD(DAY,-20,CAST(GETDATE() AS DATE)),'SUS');
GO

-- EmpleadosSalud (18 registros, algunos formatos sucios en nombres)
INSERT INTO bronze.EmpleadosSalud (Nombres, Apellidos, Cargo, Especialidad, HospitalID, FechaIngreso, Turno, CorreoInstitucional)
VALUES
('Carlos','Quispe Flores','Medico','Medicina Interna',1,'2018-02-01','Rotativo','cquispe@salud.bo'),
('  maria ','Lima Rojas','Enfermeria',NULL,1,'2019-07-12','Noche','mlima@salud.bo'),
('Jorge','Apaza Mamani','Medico','Pediatria',2,'2017-05-03','Manana','japaza@salud.bo'),
('Elena','Vargas Nina','Farmacia',NULL,2,'2020-09-10','Tarde','evargas@salud.bo'),
('Pedro','Gonzales Aramayo','Medico','Oncologia',4,'2016-01-18','Rotativo','pgonzales@salud.bo'),
('Luisa','Choque Ticona','Epidemiologia',NULL,4,'2021-03-22','Manana','lchoque@salud.bo'),
('Marco','Villca Quisbert','Medico','Ginecologia',5,'2015-11-09','Rotativo','mvillca@salud.bo'),
('Rosa','Paredes Mejia','Enfermeria',NULL,5,'2022-02-11','Tarde','rparedes@salud.bo'),
('Edgar','Mamani Chura','Bioquimica','Laboratorio Clinico',7,'2019-10-15','Manana','emamani@salud.bo'),
('claudia','Torrez Rivas','Medico','Emergencias',7,'2020-04-25','Noche','ctorrez@salud.bo'),
('Juan Pablo','Rivera Condori','Administrativo',NULL,8,'2014-06-30','Manana','jrivera@salud.bo'),
('Erika','Solis Rocabado','Medico','Cardiologia',8,'2013-08-14','Rotativo','esolis@salud.bo'),
('Ronald','Arias Quispe','Enfermeria',NULL,9,'2018-12-03','Tarde','rarias@salud.bo'),
('Silvia','Mendez Poma','Medico','Infectologia',14,'2017-09-21','Rotativo','smendez@salud.bo'),
('Hector','Loza Fernandez','Farmacia',NULL,14,'2021-01-13','Manana','hloza@salud.bo'),
('Paola','Cruz Aguilar','Medico','Nefrologia',3,'2016-10-01','Rotativo','pcruz@salud.bo'),
('William','Camacho Vera','Epidemiologia',NULL,3,'2022-06-18','Tarde','wcamacho@salud.bo'),
('Andrea','Rojas Flores','Medico','Medicina Familiar',10,'2019-11-05','Manana','arojas@salud.bo');
GO

-- Medicamentos (18 registros)
INSERT INTO bronze.Medicamentos (NombreComercial, Categoria, Presentacion, CostoUnitarioBs, StockMinimo, RequiereCadenaFrio, EstadoRegulatorio)
VALUES
('Paracetamol 500 mg','Analgesico','Tabletas x 100',25.00,300,0,'Vigente'),
('Ibuprofeno 400 mg','Antiinflamatorio','Tabletas x 100',38.00,250,0,'Vigente'),
('Amoxicilina 500 mg','Antibiotico','Capsulas x 100',65.00,220,0,'Vigente'),
('Ceftriaxona 1 g','Antibiotico','Ampolla',18.00,180,0,'Vigente'),
('Metformina 850 mg','Cronicos','Tabletas x 100',42.00,260,0,'Vigente'),
('Insulina NPH','Cronicos','Vial 10 ml',95.00,120,1,'Vigente'),
('Salbutamol','Respiratorio','Inhalador',45.00,140,0,'Vigente'),
('Oxigeno medicinal','Insumos','Balon unitario',180.00,60,0,'Vigente'),
('Doxorrubicina','Oncologia','Vial',420.00,40,1,'Vigente'),
('Cisplatino','Oncologia','Vial',360.00,35,1,'Vigente'),
('Paclitaxel','Oncologia','Vial',610.00,25,1,'Vigente'),
('Sulfato ferroso','Materno Infantil','Tabletas x 100',22.00,280,0,'Vigente'),
('Acido folico','Materno Infantil','Tabletas x 100',19.00,290,0,'Vigente'),
('Sueros isotónicos','Insumos','Bolsa 1L',12.00,500,0,'Vigente'),
('Reactivo dengue NS1','Diagnostico','Kit x 25',210.00,45,1,'EnRevision'),
('Tiras de glucosa','Diagnostico','Caja x 50',78.00,130,0,'Vigente'),
('Heparina','Emergencias','Ampolla',33.00,150,0,'Vigente'),
('Kit bioseguridad','Insumos','Unidad',27.00,170,0,'Vigente');
GO

/* ============================================================
   5) SEEDING MASIVO TABLA TRANSACCIONAL (>=1000)
      - 1200 registros
      - fechas ultimos 3 anios
      - 5% NULL deliberado en columnas no criticas
      - algunos textos con espacios extra / mayus-minus mezcladas
   ============================================================ */

DECLARE 
    @i INT = 1,
    @Total INT = 1200,
    @PacienteID INT,
    @HospitalOrigenID INT,
    @HospitalDestinoID INT,
    @EmpleadoID INT,
    @MedicamentoID INT,
    @TipoEvento VARCHAR(20),
    @EnfermedadPrincipal NVARCHAR(80),
    @DiagnosticoSecundario NVARCHAR(120),
    @Cantidad INT,
    @CostoTotalBs DECIMAL(12,2),
    @TiempoEsperaMin INT,
    @EstadoAtencion VARCHAR(20),
    @CanalIngreso VARCHAR(20),
    @Observaciones NVARCHAR(250),
    @FechaEvento DATETIME2(0),
    @r INT;

WHILE @i <= @Total
BEGIN
    -- Semilla pseudo-aleatoria por iteracion
    SET @r = ABS(CHECKSUM(NEWID())) % 100 + 1; -- 1..100

    -- Selecciones aleatorias de FK
    SELECT TOP 1 @PacienteID = PacienteID FROM bronze.Pacientes ORDER BY NEWID();
    SELECT TOP 1 @HospitalOrigenID = HospitalID FROM bronze.Hospitales ORDER BY NEWID();
    SELECT TOP 1 @HospitalDestinoID = HospitalID FROM bronze.Hospitales ORDER BY NEWID();
    SELECT TOP 1 @EmpleadoID = EmpleadoID FROM bronze.EmpleadosSalud ORDER BY NEWID();
    SELECT TOP 1 @MedicamentoID = MedicamentoID FROM bronze.Medicamentos ORDER BY NEWID();

    -- Evitar (en lo posible) mismo hospital origen-destino
    IF @HospitalDestinoID = @HospitalOrigenID
        SELECT TOP 1 @HospitalDestinoID = HospitalID FROM bronze.Hospitales WHERE HospitalID <> @HospitalOrigenID ORDER BY NEWID();

    -- Tipo de evento
    SET @TipoEvento =
        CASE ABS(CHECKSUM(NEWID())) % 5
            WHEN 0 THEN 'Consulta'
            WHEN 1 THEN 'Emergencia'
            WHEN 2 THEN 'Referencia'
            WHEN 3 THEN 'Hospitalizacion'
            ELSE 'Farmacia'
        END;

    -- Enfermedad principal (alineada al proyecto)
    SET @EnfermedadPrincipal =
        CASE ABS(CHECKSUM(NEWID())) % 8
            WHEN 0 THEN N'Cancer cervico uterino'
            WHEN 1 THEN N'Diabetes mellitus tipo 2'
            WHEN 2 THEN N'Dengue grave'
            WHEN 3 THEN N'Complicacion materna'
            WHEN 4 THEN N'Insuficiencia renal cronica'
            WHEN 5 THEN N'Neumonia adquirida'
            WHEN 6 THEN N'Infeccion respiratoria aguda'
            ELSE N'Hipertension arterial'
        END;

    -- Diagnostico secundario (5% NULL deliberado + suciedad en texto)
    SET @DiagnosticoSecundario =
        CASE 
            WHEN @r <= 5 THEN NULL
            WHEN @r BETWEEN 6 AND 15 THEN N'  anemia leve  '
            WHEN @r BETWEEN 16 AND 25 THEN N'Riesgo obstetrico MODERADO'
            WHEN @r BETWEEN 26 AND 35 THEN N'deshidratacion  '
            WHEN @r BETWEEN 36 AND 45 THEN N'coMorbilidad metabolica'
            ELSE N'Sin complicaciones mayores'
        END;

    -- Cantidad y costo (coherente salud publica)
    SET @Cantidad =
        CASE 
            WHEN @TipoEvento IN ('Farmacia','Hospitalizacion','Emergencia') THEN (ABS(CHECKSUM(NEWID())) % 5) + 1
            ELSE (ABS(CHECKSUM(NEWID())) % 2) + 1
        END;

    SET @CostoTotalBs =
        CASE @TipoEvento
            WHEN 'Consulta' THEN CAST((ABS(CHECKSUM(NEWID())) % 120) + 30 AS DECIMAL(12,2))
            WHEN 'Emergencia' THEN CAST((ABS(CHECKSUM(NEWID())) % 350) + 120 AS DECIMAL(12,2))
            WHEN 'Referencia' THEN CAST((ABS(CHECKSUM(NEWID())) % 480) + 160 AS DECIMAL(12,2))
            WHEN 'Hospitalizacion' THEN CAST((ABS(CHECKSUM(NEWID())) % 1500) + 400 AS DECIMAL(12,2))
            ELSE CAST((ABS(CHECKSUM(NEWID())) % 300) + 40 AS DECIMAL(12,2))
        END;

    SET @TiempoEsperaMin = (ABS(CHECKSUM(NEWID())) % 220) + 10;

    SET @EstadoAtencion =
        CASE ABS(CHECKSUM(NEWID())) % 10
            WHEN 0 THEN 'Pendiente'
            WHEN 1 THEN 'Suspendido'
            WHEN 2 THEN 'Derivado'
            ELSE 'Atendido'
        END;

    -- Canal ingreso (5% NULL deliberado)
    SET @CanalIngreso =
        CASE 
            WHEN @r <= 5 THEN NULL
            WHEN @TipoEvento = 'Referencia' THEN 'Referencia'
            WHEN ABS(CHECKSUM(NEWID())) % 3 = 0 THEN 'Emergencia'
            WHEN ABS(CHECKSUM(NEWID())) % 3 = 1 THEN 'ConsultaExterna'
            ELSE 'Programado'
        END;

    -- Observaciones (5% NULL deliberado + texto sucio)
    SET @Observaciones =
        CASE 
            WHEN @r <= 5 THEN NULL
            WHEN @r BETWEEN 6 AND 10 THEN N' paciente llega con retraso '
            WHEN @r BETWEEN 11 AND 15 THEN N'STOCK CRITICO en farmacia'
            WHEN @r BETWEEN 16 AND 20 THEN N'  requiere seguimiento en 48h'
            ELSE N'Atencion dentro de parametros clinicos'
        END;

    -- Fecha en ultimos 3 anios
    SET @FechaEvento = DATEADD(DAY, -1 * (ABS(CHECKSUM(NEWID())) % 1095), CAST(GETDATE() AS DATE));
    SET @FechaEvento = DATEADD(MINUTE, ABS(CHECKSUM(NEWID())) % 1440, @FechaEvento);

    INSERT INTO bronze.EventosSalud
    (
        FechaEvento,
        TipoEvento,
        PacienteID,
        HospitalOrigenID,
        HospitalDestinoID,
        EmpleadoID,
        MedicamentoID,
        EnfermedadPrincipal,
        DiagnosticoSecundario,
        Cantidad,
        CostoTotalBs,
        TiempoEsperaMin,
        EstadoAtencion,
        CanalIngreso,
        Observaciones
    )
    VALUES
    (
        @FechaEvento,
        @TipoEvento,
        @PacienteID,
        @HospitalOrigenID,
        CASE WHEN @TipoEvento = 'Referencia' THEN @HospitalDestinoID ELSE NULL END,
        @EmpleadoID,
        CASE WHEN @TipoEvento IN ('Farmacia','Hospitalizacion','Emergencia') THEN @MedicamentoID ELSE NULL END,
        @EnfermedadPrincipal,
        @DiagnosticoSecundario,
        @Cantidad,
        @CostoTotalBs,
        @TiempoEsperaMin,
        @EstadoAtencion,
        @CanalIngreso,
        @Observaciones
    );

    SET @i += 1;
END;
GO

/* ============================================================
   6) VALIDACIONES RAPIDAS
   ============================================================ */
SELECT 'Geografia' AS Tabla, COUNT(*) AS Registros FROM bronze.Geografia
UNION ALL
SELECT 'Hospitales', COUNT(*) FROM bronze.Hospitales
UNION ALL
SELECT 'Pacientes', COUNT(*) FROM bronze.Pacientes
UNION ALL
SELECT 'EmpleadosSalud', COUNT(*) FROM bronze.EmpleadosSalud
UNION ALL
SELECT 'Medicamentos', COUNT(*) FROM bronze.Medicamentos
UNION ALL
SELECT 'EventosSalud', COUNT(*) FROM bronze.EventosSalud;
GO

-- Verificar % NULL aproximado en columnas no criticas de la transaccional
SELECT
    COUNT(*) AS TotalEventos,
    SUM(CASE WHEN DiagnosticoSecundario IS NULL THEN 1 ELSE 0 END) AS Null_DiagnosticoSecundario,
    SUM(CASE WHEN CanalIngreso IS NULL THEN 1 ELSE 0 END) AS Null_CanalIngreso,
    SUM(CASE WHEN Observaciones IS NULL THEN 1 ELSE 0 END) AS Null_Observaciones,
    CAST(100.0 * SUM(CASE WHEN DiagnosticoSecundario IS NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,2)) AS PctNull_DiagnosticoSecundario,
    CAST(100.0 * SUM(CASE WHEN CanalIngreso IS NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,2)) AS PctNull_CanalIngreso,
    CAST(100.0 * SUM(CASE WHEN Observaciones IS NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,2)) AS PctNull_Observaciones
FROM bronze.EventosSalud;
GO
