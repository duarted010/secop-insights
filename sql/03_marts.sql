-- Marts: small, query-ready tables that answer specific questions.
-- Rebuilt on every run (cheap at this data size, and always consistent with staging).
CREATE SCHEMA IF NOT EXISTS marts;

-- 1) Monthly spend per department
DROP TABLE IF EXISTS marts.monthly_spend_by_department;
CREATE TABLE marts.monthly_spend_by_department AS
SELECT
    date_trunc('month', fecha_firma)::DATE AS mes,
    departamento,
    count(*)                               AS contratos,
    sum(valor_contrato)                    AS valor_total,
    round(avg(valor_contrato))             AS valor_promedio
FROM staging.contracts
WHERE fecha_firma IS NOT NULL AND valor_contrato IS NOT NULL
GROUP BY 1, 2;

-- 2) How much is awarded without competition (direct contracting), per entity
DROP TABLE IF EXISTS marts.direct_contracting_by_entity;
CREATE TABLE marts.direct_contracting_by_entity AS
SELECT
    entidad,
    departamento,
    count(*)                                                        AS contratos,
    count(*) FILTER (WHERE es_contratacion_directa)                 AS contratos_directos,
    round(100.0 * count(*) FILTER (WHERE es_contratacion_directa) / count(*), 1) AS pct_contratos_directos,
    sum(valor_contrato)                                             AS valor_total,
    round(100.0 * sum(valor_contrato) FILTER (WHERE es_contratacion_directa)
          / NULLIF(sum(valor_contrato), 0), 1)                      AS pct_valor_directo
FROM staging.contracts
GROUP BY 1, 2;

-- 3) Supplier concentration per entity (Herfindahl-Hirschman Index on contract value, companies only).
--    HHI near 10,000 = one supplier gets everything; below 1,500 = competitive.
DROP TABLE IF EXISTS marts.supplier_concentration;
CREATE TABLE marts.supplier_concentration AS
WITH shares AS (
    SELECT entidad, proveedor,
           sum(valor_contrato) / NULLIF(sum(sum(valor_contrato)) OVER (PARTITION BY entidad), 0) AS share
    FROM staging.contracts
    WHERE proveedor_es_empresa AND proveedor IS NOT NULL AND valor_contrato > 0
    GROUP BY entidad, proveedor
)
SELECT
    entidad,
    count(*)                              AS proveedores,
    round(sum((share * 100) ^ 2))         AS hhi,
    round(100 * max(share), 1)            AS pct_mayor_proveedor
FROM shares
GROUP BY entidad;

-- 4) Contract extensions: how often and how long contracts get extended, by contracting modality
DROP TABLE IF EXISTS marts.extensions_by_modality;
CREATE TABLE marts.extensions_by_modality AS
SELECT
    modalidad,
    count(*)                                              AS contratos,
    round(100.0 * count(*) FILTER (WHERE dias_adicionados > 0) / count(*), 1) AS pct_con_prorroga,
    round(avg(dias_adicionados) FILTER (WHERE dias_adicionados > 0), 1)       AS dias_prorroga_promedio,
    round(avg(duracion_dias), 1)                          AS duracion_promedio_dias
FROM staging.contracts
WHERE modalidad IS NOT NULL
GROUP BY modalidad;

-- 5) SME (pyme) participation by sector
DROP TABLE IF EXISTS marts.pyme_share_by_sector;
CREATE TABLE marts.pyme_share_by_sector AS
SELECT
    sector,
    count(*) FILTER (WHERE proveedor_es_empresa)                         AS contratos_con_empresas,
    round(100.0 * count(*) FILTER (WHERE proveedor_es_empresa AND es_pyme)
          / NULLIF(count(*) FILTER (WHERE proveedor_es_empresa), 0), 1) AS pct_pyme,
    round(100.0 * sum(valor_contrato) FILTER (WHERE proveedor_es_empresa AND es_pyme)
          / NULLIF(sum(valor_contrato) FILTER (WHERE proveedor_es_empresa), 0), 1) AS pct_valor_pyme
FROM staging.contracts
WHERE sector IS NOT NULL
GROUP BY sector;
