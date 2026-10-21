-- Staging layer: typed, trimmed and normalized. Bad values become NULL instead of failing the load;
-- the data-quality checks (pipeline/quality.py) report how many rows were affected.
CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE FUNCTION staging.to_num(v TEXT) RETURNS NUMERIC
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN v ~ '^-?[0-9]+(\.[0-9]+)?$' THEN v::NUMERIC END
$$;

CREATE OR REPLACE FUNCTION staging.to_date(v TEXT) RETURNS DATE
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN v ~ '^\d{4}-\d{2}-\d{2}' THEN substr(v, 1, 10)::DATE END
$$;

CREATE OR REPLACE VIEW staging.contracts AS
SELECT
    id_contrato,
    trim(nombre_entidad)                              AS entidad,
    nit_entidad,
    initcap(trim(departamento))                       AS departamento,
    initcap(trim(ciudad))                             AS ciudad,
    orden,
    sector,
    proceso_de_compra,
    estado_contrato,
    codigo_de_categoria_principal                     AS categoria_unspsc,
    objeto_del_contrato                               AS objeto,
    tipo_de_contrato,
    modalidad_de_contratacion                         AS modalidad,
    (modalidad_de_contratacion = 'Contratación directa') AS es_contratacion_directa,
    staging.to_date(fecha_de_firma)                   AS fecha_firma,
    staging.to_date(fecha_de_inicio_del_contrato)     AS fecha_inicio,
    staging.to_date(fecha_de_fin_del_contrato)        AS fecha_fin,
    (tipodocproveedor = 'NIT')                        AS proveedor_es_empresa,
    proveedor_adjudicado                              AS proveedor,
    (es_pyme = 'Si')                                  AS es_pyme,
    destino_gasto,
    staging.to_num(valor_del_contrato)                AS valor_contrato,
    staging.to_num(valor_pagado)                      AS valor_pagado,
    staging.to_num(valor_facturado)                   AS valor_facturado,
    COALESCE(staging.to_num(dias_adicionados), 0)::INT AS dias_adicionados,
    staging.to_date(fecha_de_fin_del_contrato) - staging.to_date(fecha_de_inicio_del_contrato) AS duracion_dias,
    url_proceso,
    _loaded_at
FROM raw.secop_contracts;
