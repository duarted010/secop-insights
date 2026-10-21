"""Generate charts + a findings summary from the marts.   python -m analysis.report"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from pipeline.config import settings  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs"


def money(v) -> str:
    v = float(v or 0)
    return f"${v / 1e9:,.1f} mil millones" if v >= 1e9 else f"${v / 1e6:,.1f} millones"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        q = lambda sql: conn.execute(sql).fetchall()  # noqa: E731
        totals = q("SELECT count(*) n, sum(valor_contrato) v, min(fecha_firma) d0, max(fecha_firma) d1, "
                   "round(100.0*avg(es_contratacion_directa::int),1) pct_dir FROM staging.contracts")[0]
        top_dept = q("SELECT departamento, sum(valor_total) v FROM marts.monthly_spend_by_department "
                     "GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
        modal = q("SELECT * FROM marts.extensions_by_modality ORDER BY contratos DESC LIMIT 8")
        conc = q("SELECT * FROM marts.supplier_concentration WHERE proveedores >= 5 ORDER BY hhi DESC LIMIT 5")
        direct = q("SELECT * FROM marts.direct_contracting_by_entity WHERE contratos >= 20 "
                   "ORDER BY pct_valor_directo DESC NULLS LAST LIMIT 5")

    # Chart 1: spend by department
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh([r["departamento"] for r in reversed(top_dept)], [float(r["v"]) / 1e9 for r in reversed(top_dept)],
            color="#2b6cb0")
    ax.set_xlabel("Valor contratado (miles de millones COP)")
    ax.set_title("Top 10 departamentos por valor contratado (SECOP II)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "spend_by_department.png", dpi=150)

    # Chart 2: extensions by modality
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh([r["modalidad"] for r in reversed(modal)], [float(r["pct_con_prorroga"] or 0) for r in reversed(modal)],
            color="#dd6b20")
    ax.set_xlabel("% de contratos con prórroga (días adicionados > 0)")
    ax.set_title("¿Qué tan seguido se prorrogan los contratos, por modalidad?")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "extensions_by_modality.png", dpi=150)

    lines = [
        "# Findings",
        "",
        f"Dataset: **{totals['n']:,} contracts** signed between {totals['d0']} and {totals['d1']}, "
        f"worth **{money(totals['v'])} COP**.",
        f"- **{totals['pct_dir']}%** of contracts were awarded by *contratación directa* (no competition).",
        "",
        "## Entities with the highest share of value awarded directly (≥ 20 contracts)",
        *[f"- {r['entidad']} ({r['departamento']}): {r['pct_valor_directo']}% of {money(r['valor_total'])}"
          for r in direct],
        "",
        "## Most concentrated supplier bases (HHI, ≥ 5 suppliers)",
        *[f"- {r['entidad']}: HHI {r['hhi']:,.0f}, top supplier gets {r['pct_mayor_proveedor']}% of value"
          for r in conc],
        "",
        "![Spend by department](spend_by_department.png)",
        "![Extensions by modality](extensions_by_modality.png)",
    ]
    (OUT / "FINDINGS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
