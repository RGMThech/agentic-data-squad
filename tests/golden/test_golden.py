"""Executa os casos de ouro em DuckDB e compara com o resultado esperado.

Para cada pasta em tests/golden/<feature>/:
  1. carrega input/*.csv como tabelas (nome do arquivo = nome da tabela)
  2. executa os pipelines SQL listados em caso.yaml, na ordem
  3. compara cada expected/<tabela>.csv com o resultado
  4. roda as verificações derivadas do contrato de cada tabela gerada
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "quality"))
import contract_checks  # noqa: E402

CASOS = sorted(p for p in Path(__file__).parent.iterdir() if (p / "caso.yaml").exists())


def _normalizar(v):
    if v is None or v == "":
        return None
    if isinstance(v, (Decimal, float)):
        return f"{float(v):.2f}"
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if isinstance(v, int):
        return str(v)
    s = str(v)
    try:
        return f"{float(s):.2f}" if "." in s else s
    except ValueError:
        return s


def _linhas(cabecalho, linhas):
    return sorted(tuple(_normalizar(x) for x in l) for l in linhas), list(cabecalho)


def _executar(con, caso_dir: Path) -> list[str]:
    caso = yaml.safe_load((caso_dir / "caso.yaml").read_text(encoding="utf-8"))
    for arq in sorted((caso_dir / "input").glob("*.csv")):
        con.execute(f"CREATE TABLE {arq.stem} AS SELECT * FROM read_csv_auto(?, header=true)", [str(arq)])
    geradas = []
    for rel in caso["pipelines"]:
        sql_path = ROOT / rel
        nome = sql_path.stem
        con.execute(f"CREATE TABLE {nome} AS {sql_path.read_text(encoding='utf-8')}")
        geradas.append(nome)
    return geradas


@pytest.mark.parametrize("caso_dir", CASOS, ids=[c.name for c in CASOS])
def test_resultado_igual_ao_esperado(caso_dir: Path):
    con = duckdb.connect()
    _executar(con, caso_dir)
    for esperado in sorted((caso_dir / "expected").glob("*.csv")):
        with esperado.open(encoding="utf-8") as f:
            leitor = csv.reader(f)
            cab = next(leitor)
            exp, _ = _linhas(cab, leitor)
        rel = con.execute(f"SELECT {', '.join(cab)} FROM {esperado.stem}")
        obt, _ = _linhas(cab, rel.fetchall())
        assert obt == exp, f"{caso_dir.name}/{esperado.stem}: resultado difere do esperado\nobtido={obt}\nesperado={exp}"


@pytest.mark.parametrize("caso_dir", CASOS, ids=[c.name for c in CASOS])
def test_contrato_das_tabelas_geradas(caso_dir: Path):
    con = duckdb.connect()
    for tabela in _executar(con, caso_dir):
        contrato_path = ROOT / "contracts" / f"{tabela}.yaml"
        if not contrato_path.exists():
            continue
        contrato = yaml.safe_load(contrato_path.read_text(encoding="utf-8"))

        colunas_reais = {r[0] for r in con.execute(f"DESCRIBE {tabela}").fetchall()}
        colunas_contrato = {c["nome"] for c in contrato["colunas"]}
        assert colunas_reais == colunas_contrato, (
            f"{tabela}: schema difere do contrato. "
            f"Sobrando: {colunas_reais - colunas_contrato}; faltando: {colunas_contrato - colunas_reais}"
        )

        for v in contract_checks.gerar(contrato):
            violacoes = con.execute(v.sql).fetchone()[0]
            assert violacoes == 0, f"{tabela}: {v.nome} com {violacoes} violação(ões)"

        if contrato["camada"] == "gold":
            assert not contract_checks.colunas_pii(contrato), f"{tabela}: gold não pode ter coluna PII"
