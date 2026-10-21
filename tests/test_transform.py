from pipeline.transform import COLUMNS, to_row, to_rows

BASE = {
    "id_contrato": "CO1.PCCNTR.1", "nombre_entidad": "  Entidad X ", "tipodocproveedor": "NIT",
    "proveedor_adjudicado": "Empresa S.A.S.", "valor_del_contrato": "1000",
    "urlproceso": {"url": "https://example.org/p/1"},
    "n_mero_de_cuenta": "123456789", "nombre_supervisor": "Someone", "documento_proveedor": "900",
}


def test_only_whitelisted_columns_are_kept():
    row = to_row(BASE)
    assert set(row) == set(COLUMNS)
    assert "n_mero_de_cuenta" not in row and "nombre_supervisor" not in row


def test_natural_person_supplier_name_is_dropped():
    row = to_row({**BASE, "tipodocproveedor": "Cédula de Ciudadanía", "proveedor_adjudicado": "Ana Pérez"})
    assert row["proveedor_adjudicado"] is None


def test_company_supplier_name_is_kept_and_strings_are_trimmed():
    row = to_row(BASE)
    assert row["proveedor_adjudicado"] == "Empresa S.A.S."
    assert row["nombre_entidad"] == "Entidad X"


def test_placeholder_values_become_null_and_url_is_flattened():
    row = to_row({**BASE, "estado_contrato": "No definido"})
    assert row["estado_contrato"] is None
    assert row["url_proceso"] == "https://example.org/p/1"


def test_records_without_id_are_skipped_and_duplicates_collapsed():
    rows = to_rows([BASE, {**BASE, "valor_del_contrato": "2000"}, {**BASE, "id_contrato": ""}])
    assert len(rows) == 1
    assert rows[0]["valor_del_contrato"] == "2000"
