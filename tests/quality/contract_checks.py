"""Gera verificações de qualidade (SQL) a partir de um data contract.

Cada verificação é uma consulta que retorna a QUANTIDADE DE VIOLAÇÕES.
Zero = aprovado. O SQL é ANSI e roda em DuckDB (testes locais) e, com poucos
ajustes, em Spark SQL, Snowflake, BigQuery etc.

# PLATAFORMA: para rodar no seu ambiente dev, execute os SQLs gerados com o
# cliente da sua engine ou traduza para Great Expectations / dbt tests / DLT expectations.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Verificacao:
    nome: str
    sql: str


def _q(valor) -> str:
    return "'" + str(valor).replace("'", "''") + "'"


def gerar(contrato: dict, tabela: str | None = None) -> list[Verificacao]:
    t = tabela or contrato["tabela"]
    checks: list[Verificacao] = []

    chave = ", ".join(contrato["chave"])
    checks.append(Verificacao(
        f"unicidade[{chave}]",
        f"SELECT COUNT(*) FROM (SELECT {chave} FROM {t} GROUP BY {chave} HAVING COUNT(*) > 1) d",
    ))

    for col in contrato["colunas"]:
        n = col["nome"]
        if col.get("nulo") is False:
            checks.append(Verificacao(f"not_null[{n}]", f"SELECT COUNT(*) FROM {t} WHERE {n} IS NULL"))
        if "valores_aceitos" in col:
            lista = ", ".join(_q(v) for v in col["valores_aceitos"])
            checks.append(Verificacao(
                f"dominio[{n}]", f"SELECT COUNT(*) FROM {t} WHERE {n} IS NOT NULL AND {n} NOT IN ({lista})"
            ))
        if "min" in col:
            checks.append(Verificacao(f"min[{n}]", f"SELECT COUNT(*) FROM {t} WHERE {n} < {col['min']}"))
        if "max" in col:
            checks.append(Verificacao(f"max[{n}]", f"SELECT COUNT(*) FROM {t} WHERE {n} > {col['max']}"))
    return checks


def colunas_pii(contrato: dict) -> list[str]:
    return [c["nome"] for c in contrato["colunas"] if c.get("pii")]
