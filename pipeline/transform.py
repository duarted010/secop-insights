"""Turn raw API records into rows for raw.secop_contracts.

Privacy by design: SECOP publishes personal data (ID numbers, bank accounts, names of officials
and of individual contractors). Only an explicit whitelist of columns is kept, and the supplier
name is dropped when the supplier is a natural person (anything other than a NIT).
"""
from __future__ import annotations

COLUMNS = [
    "id_contrato", "nombre_entidad", "nit_entidad", "departamento", "ciudad", "orden", "sector",
    "proceso_de_compra", "estado_contrato", "codigo_de_categoria_principal", "objeto_del_contrato",
    "tipo_de_contrato", "modalidad_de_contratacion", "fecha_de_firma", "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato", "tipodocproveedor", "proveedor_adjudicado", "es_pyme", "destino_gasto",
    "valor_del_contrato", "valor_pagado", "valor_facturado", "dias_adicionados", "url_proceso",
]

COMPANY_DOC_TYPES = {"NIT"}


def to_row(record: dict) -> dict | None:
    """Return a whitelisted, PII-free row, or None if the record has no contract id."""
    if not record.get("id_contrato"):
        return None
    row = {col: record.get(col) for col in COLUMNS if col != "url_proceso"}
    url = record.get("urlproceso")
    row["url_proceso"] = url.get("url") if isinstance(url, dict) else url
    if record.get("tipodocproveedor") not in COMPANY_DOC_TYPES:
        row["proveedor_adjudicado"] = None  # natural person: do not store their name
    for key, value in row.items():
        if isinstance(value, str):
            value = value.strip()
            row[key] = None if value in ("", "No definido", "No Definido", "Sin Descripcion") else value
    return row


def to_rows(records: list[dict]) -> list[dict]:
    rows = {}
    for rec in records:
        row = to_row(rec)
        if row:
            rows[row["id_contrato"]] = row  # last one wins if the API returns duplicates
    return list(rows.values())
