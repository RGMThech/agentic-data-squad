"""Testes do acesso dos agentes ao Databricks (scripts/dbx.py)."""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import dbx  # noqa: E402

ESCRITA = "squad_dev.agentes"


# ----------------------------------------------------------------- travas de SQL

@pytest.mark.parametrize("sql", [
    "SELECT * FROM vendas.silver.pedidos",
    "with x as (select 1) select * from x",
    "SHOW TABLES IN vendas.silver",
    "DESCRIBE TABLE vendas.silver.pedidos",
    "SELECT update_ts, created_by FROM t",                 # palavras parecidas não confundem
    "SELECT 'DROP TABLE x; GRANT ALL' AS texto",           # literais não contam
    "SELECT 1; -- comentário com ; no fim",
])
def test_leitura_permitida(sql):
    assert dbx.validar_sql(sql, ESCRITA) == "leitura"


@pytest.mark.parametrize("sql", [
    "CREATE OR REPLACE TABLE squad_dev.agentes.slv_vendas__pedidos AS SELECT 1",
    "INSERT INTO `squad_dev`.`agentes`.`x` SELECT 1",
    "MERGE INTO squad_dev.agentes.x t USING src s ON t.id = s.id WHEN MATCHED THEN UPDATE SET *",
    "DROP TABLE IF EXISTS squad_dev.agentes.tmp",
    "CREATE VIEW squad_dev.agentes.v AS SELECT * FROM vendas.silver.pedidos",
])
def test_escrita_na_sandbox(sql):
    assert dbx.validar_sql(sql, ESCRITA) == "escrita"


@pytest.mark.parametrize("sql, trecho", [
    ("INSERT INTO vendas.silver.pedidos SELECT 1", "fora da sandbox"),
    ("CREATE TABLE squad_dev.outro.x AS SELECT 1", "fora da sandbox"),
    ("DROP TABLE pedidos", "nome completo"),
    ("DELETE FROM producao.gold.receita WHERE 1=1", "fora da sandbox"),
    ("GRANT SELECT ON TABLE x TO `y`", "não é permitido"),
    ("ALTER TABLE squad_dev.agentes.x SET OWNER TO `alguem`", "não é permitido"),
    ("SELECT 1; DROP TABLE squad_dev.agentes.x", "uma instrução por vez"),
    ("WITH s AS (SELECT 1) INSERT INTO prod.gold.x SELECT * FROM s", "fora da sandbox"),
    ("UPDATE producao.gold.receita SET valor_vl = 0", "fora da sandbox"),
    ("", "vazia"),
])
def test_bloqueios(sql, trecho):
    with pytest.raises(dbx.Erro, match=trecho):
        dbx.validar_sql(sql, ESCRITA)


def test_sem_schema_de_escrita_bloqueia_qualquer_escrita():
    with pytest.raises(dbx.Erro, match="Escrita bloqueada"):
        dbx.validar_sql("CREATE TABLE squad_dev.agentes.x AS SELECT 1", "")


def test_mascara_colunas_pessoais():
    linhas, mascaradas = dbx.mascarar(["pedido_id", "cliente_cpf", "email", "valor_vl"], [["P1", "123", "a@b.com", "10.0"], ["P2", None, "", "5"]])
    assert mascaradas == ["cliente_cpf", "email"]
    assert linhas == [["P1", "•••", "•••", "10.0"], ["P2", None, "", "5"]]


def test_sem_configuracao_orienta_o_operador(capsys, monkeypatch, tmp_path):
    for k in ("DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(dbx, "_yaml", lambda: {})
    assert dbx.main(["testar"]) == 1
    err = capsys.readouterr().err
    assert "Squad Console" in err and "Não peça credenciais" in err


# ----------------------------------------------------------------- integração com Databricks simulado

class FakeDatabricks(BaseHTTPRequestHandler):
    statements: dict = {}
    pedidos: list = []

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        tam = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tam).decode()
        if self.path == "/oidc/v1/token":
            if self.headers.get("Authorization") != "Basic " + __import__("base64").b64encode(b"cid:segredo").decode():
                return self._json(401, {"error": "invalid_client", "error_description": "Client authentication failed"})
            assert "grant_type=client_credentials" in corpo and "scope=all-apis" in corpo
            return self._json(200, {"access_token": "tk", "token_type": "Bearer", "expires_in": 3600})
        if self.path == "/api/2.0/sql/statements/":
            assert self.headers.get("Authorization") == "Bearer tk"
            j = json.loads(corpo)
            FakeDatabricks.pedidos.append(j)
            if j["warehouse_id"] != "wh1":
                return self._json(404, {"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "warehouse wh9 does not exist"})
            FakeDatabricks.statements["s1"] = 0
            return self._json(200, {"statement_id": "s1", "status": {"state": "PENDING"}})
        self._json(404, {})

    def do_GET(self):
        if self.path == "/api/2.0/sql/statements/s1":
            FakeDatabricks.statements["s1"] += 1
            if FakeDatabricks.statements["s1"] < 2:
                return self._json(200, {"statement_id": "s1", "status": {"state": "RUNNING"}})
            return self._json(200, {
                "statement_id": "s1",
                "status": {"state": "SUCCEEDED"},
                "manifest": {"schema": {"columns": [{"name": "loja_cd"}, {"name": "cliente_email"}]}, "total_row_count": 2},
                "result": {"data_array": [["L01", "a@b.com"], ["L02", None]]},
            })
        self._json(404, {})


@pytest.fixture
def databricks(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), FakeDatabricks)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(dbx.time, "sleep", lambda s: None)
    monkeypatch.setattr(dbx, "_yaml", lambda: {"host": f"http://127.0.0.1:{srv.server_port}", "warehouse_id": "wh1", "escrita": ESCRITA, "leitura": ["vendas"]})
    monkeypatch.setenv("DATABRICKS_CLIENT_ID", "cid")
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "segredo")
    FakeDatabricks.pedidos.clear()
    yield srv
    srv.shutdown()


def test_consulta_ponta_a_ponta(databricks, capsys):
    assert dbx.main(["sql", "SELECT loja_cd, cliente_email FROM vendas.silver.clientes", "--linhas", "500"]) == 0
    out = capsys.readouterr().out
    assert "| loja_cd | cliente_email |" in out
    assert "| L01 | ••• |" in out and "a@b.com" not in out
    assert "colunas mascaradas" in out
    pedido = FakeDatabricks.pedidos[-1]
    assert pedido["row_limit"] == dbx.LIMITE_MAXIMO, "limite máximo respeitado"
    assert pedido["disposition"] == "INLINE"


def test_credenciais_erradas(databricks, monkeypatch, capsys):
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "errado")
    assert dbx.main(["testar"]) == 1
    assert "Credenciais recusadas" in capsys.readouterr().err


def test_warehouse_inexistente(databricks, monkeypatch, capsys):
    monkeypatch.setattr(dbx, "_yaml", lambda: {"host": f"http://127.0.0.1:{databricks.server_port}", "warehouse_id": "wh9"})
    assert dbx.main(["testar"]) == 1
    assert "warehouse não encontrado" in capsys.readouterr().err


def test_escrita_fora_da_sandbox_nem_chega_ao_databricks(databricks, capsys):
    assert dbx.main(["sql", "DROP TABLE producao.gold.receita"]) == 1
    assert FakeDatabricks.pedidos == []
