-- Raw layer: one row per SECOP II contract, only whitelisted (non-personal) columns.
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.secop_contracts (
    id_contrato                  TEXT PRIMARY KEY,
    nombre_entidad               TEXT,
    nit_entidad                  TEXT,
    departamento                 TEXT,
    ciudad                       TEXT,
    orden                        TEXT,
    sector                       TEXT,
    proceso_de_compra            TEXT,
    estado_contrato              TEXT,
    codigo_de_categoria_principal TEXT,
    objeto_del_contrato          TEXT,
    tipo_de_contrato             TEXT,
    modalidad_de_contratacion    TEXT,
    fecha_de_firma               TEXT,
    fecha_de_inicio_del_contrato TEXT,
    fecha_de_fin_del_contrato    TEXT,
    tipodocproveedor             TEXT,
    proveedor_adjudicado         TEXT,   -- set to NULL when the supplier is a natural person
    es_pyme                      TEXT,
    destino_gasto                TEXT,
    valor_del_contrato           TEXT,
    valor_pagado                 TEXT,
    valor_facturado              TEXT,
    dias_adicionados             TEXT,
    url_proceso                  TEXT,
    _loaded_at                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.load_runs (
    run_id        BIGSERIAL PRIMARY KEY,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    since_date    DATE,
    rows_fetched  INTEGER,
    rows_upserted INTEGER,
    status        TEXT
);
