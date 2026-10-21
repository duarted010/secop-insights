"""Generate a SYNTHETIC sample with the same shape as the SECOP II API (for tests and offline demos).
Values are random; entity/supplier names are invented. Real data comes from `python -m pipeline.run`."""
import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
DEPTS = [("Distrito Capital de Bogotá", "Bogotá"), ("Antioquia", "Medellín"), ("Valle del Cauca", "Cali"),
         ("Atlántico", "Barranquilla"), ("Santander", "Bucaramanga"), ("Cesar", "Valledupar")]
SECTORS = ["Educación Nacional", "Salud y Protección Social", "Cultura", "Transporte", "Servicio Público"]
MODALITIES = [("Contratación directa", 0.55), ("Mínima cuantía", 0.2), ("Licitación pública", 0.1),
              ("Selección abreviada de menor cuantía", 0.1), ("Concurso de méritos abierto", 0.05)]
ENTITIES = [f"Entidad Demo {i:02d}" for i in range(1, 16)]
COMPANIES = [f"Proveedor Demo {chr(65 + i)} S.A.S." for i in range(12)]


def pick_modality():
    r, acc = random.random(), 0.0
    for name, p in MODALITIES:
        acc += p
        if r <= acc:
            return name
    return MODALITIES[0][0]


def record(i: int) -> dict:
    dept, city = random.choice(DEPTS)
    signed = date(2025, 1, 1) + timedelta(days=random.randint(0, 600))
    start = signed + timedelta(days=random.randint(0, 10))
    end = start + timedelta(days=random.randint(30, 330))
    is_company = random.random() < 0.45
    value = random.choice([3, 6, 8, 12, 25, 60, 150, 900]) * 1_000_000
    return {
        "nombre_entidad": random.choice(ENTITIES), "nit_entidad": str(800000000 + i % 15),
        "departamento": dept, "ciudad": city, "orden": random.choice(["Nacional", "Territorial"]),
        "sector": random.choice(SECTORS), "rama": "Ejecutivo",
        "proceso_de_compra": f"CO1.BDOS.{1000000 + i}", "id_contrato": f"CO1.PCCNTR.{5000000 + i}",
        "estado_contrato": random.choice(["En ejecución", "terminado", "Modificado"]),
        "codigo_de_categoria_principal": "V1.80111701", "objeto_del_contrato": "Prestación de servicios de apoyo",
        "tipo_de_contrato": "Prestación de servicios", "modalidad_de_contratacion": pick_modality(),
        "fecha_de_firma": f"{signed}T00:00:00.000", "fecha_de_inicio_del_contrato": f"{start}T00:00:00.000",
        "fecha_de_fin_del_contrato": f"{end}T00:00:00.000",
        "tipodocproveedor": "NIT" if is_company else "Cédula de Ciudadanía",
        "documento_proveedor": "900000000" if is_company else "1000000000",
        "proveedor_adjudicado": random.choice(COMPANIES) if is_company else "Persona Natural Demo",
        "es_pyme": random.choice(["Si", "No"]), "destino_gasto": random.choice(["Inversión", "Funcionamiento"]),
        "valor_del_contrato": str(value), "valor_pagado": str(int(value * random.choice([0, 0.5, 1]))),
        "valor_facturado": str(value), "dias_adicionados": str(random.choice([0, 0, 0, 0, 15, 30, 60])),
        "urlproceso": {"url": f"https://community.secop.gov.co/demo/{i}"},
        "n_mero_de_cuenta": "0000000000", "nombre_supervisor": "Supervisor Demo",  # PII fields that must be dropped
    }


rows = [record(i) for i in range(400)]
rows[10]["valor_del_contrato"] = "No definido"                 # unparseable value
rows[11]["fecha_de_fin_del_contrato"] = "2024-01-01T00:00:00.000"  # ends before it starts
rows.append(dict(rows[5]))                                     # duplicate from the API
rows.append({**rows[6], "id_contrato": ""})                    # missing id -> skipped

out = Path(__file__).parent / "fixtures" / "sample_contracts.json"
out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {len(rows)} synthetic records to {out}")
