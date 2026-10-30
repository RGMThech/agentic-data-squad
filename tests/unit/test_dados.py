"""Testes do acesso dos agentes aos dados (scripts/dados.py) nas quatro plataformas."""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import dados  # noqa: E402

ESCRITA = "squad_dev.agentes"
SEGREDOS = ("DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET", "SNOWFLAKE_PRIVATE_KEY", "GCP_SA_KEY",
            "FABRIC_CLIENT_ID", "FABRIC_CLIENT_SECRET", "DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID",
            "DADOS_PLATAFORMA", "DADOS_LEITURA", "DADOS_ESCRITA", "DADOS_URL_BASE")


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    for k in SEGREDOS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(dados.time, "sleep", lambda s: None)


def usar(monkeypatch, raiz: dict):
    monkeypatch.setattr(dados, "_raiz", lambda: raiz)


# ----------------------------------------------------------------- travas de SQL

@pytest.mark.parametrize("sql", [
    "SELECT * FROM vendas.silver.pedidos",
    "with x as (select 1) select * from x",
    "SHOW TABLES IN vendas.silver",
    "DESCRIBE TABLE vendas.silver.pedidos",
    "SELECT update_ts, created_by, call_id FROM t",        # palavras parecidas não confundem
    "SELECT 'DROP TABLE x; GRANT ALL' AS texto",           # literais não contam
    "SELECT 1; -- comentário com ; no fim",
    "SELECT TOP 10 * FROM [vendas].[dbo].[pedidos]",       # Fabric
    "SELECT * FROM `meu-projeto.vendas.pedidos` LIMIT 5",  # BigQuery
])
def test_leitura_permitida(sql):
    assert dados.validar_sql(sql, ESCRITA) == "leitura"


@pytest.mark.parametrize("sql, escrita", [
    ("CREATE OR REPLACE TABLE squad_dev.agentes.slv_vendas__pedidos AS SELECT 1", ESCRITA),
    ("INSERT INTO `squad_dev`.`agentes`.`x` SELECT 1", ESCRITA),
    ("MERGE INTO squad_dev.agentes.x t USING src s ON t.id = s.id WHEN MATCHED THEN UPDATE SET *", ESCRITA),
    ("DROP TABLE IF EXISTS squad_dev.agentes.tmp", ESCRITA),
    ("CREATE VIEW squad_dev.agentes.v AS SELECT * FROM vendas.silver.pedidos", ESCRITA),
    ("CREATE OR REPLACE TRANSIENT TABLE SQUAD_DEV.AGENTES.X AS SELECT 1", ESCRITA),        # Snowflake
    ('CREATE TABLE "SQUAD_DEV"."AGENTES"."X" (id INT)', ESCRITA),                          # Snowflake com aspas
    ("CREATE TABLE `meu-projeto.sandbox.slv_x` AS SELECT 1", "meu-projeto.sandbox"),       # BigQuery
    ("CREATE TABLE [squad_dev].[agentes].[x] (id INT)", ESCRITA),                          # Fabric
    ("SELECT a, b INTO squad_dev.agentes.copia FROM vendas.dbo.pedidos", ESCRITA),         # T-SQL SELECT INTO
])
def test_escrita_na_sandbox(sql, escrita):
    assert dados.validar_sql(sql, escrita) == "escrita"


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
    ("SELECT a INTO prod.dbo.copia FROM vendas.dbo.pedidos", "fora da sandbox"),
    ("EXEC sp_addrolemember 'db_owner', 'x'", "não é permitido"),
    ("CALL squad_dev.agentes.proc()", "não é permitido"),
    ("EXECUTE IMMEDIATE 'DROP TABLE prod.gold.x'", "não é permitido"),
    ("COPY INTO @meu_stage FROM vendas.silver.pedidos", "não é permitido|identificar"),
    ("EXPORT DATA OPTIONS(uri='gs://x/*') AS SELECT 1", "não é permitido"),
    ("SELECT * FROM OPENROWSET(BULK 'https://x/y.csv') AS r", "não é permitido"),
    ("", "vazia"),
])
def test_bloqueios(sql, trecho):
    with pytest.raises(dados.Erro, match=trecho):
        dados.validar_sql(sql, ESCRITA)


def test_sem_sandbox_bloqueia_qualquer_escrita():
    with pytest.raises(dados.Erro, match="Escrita bloqueada"):
        dados.validar_sql("CREATE TABLE squad_dev.agentes.x AS SELECT 1", "")


def test_mascara_colunas_pessoais():
    linhas, mascaradas = dados.mascarar(["pedido_id", "cliente_cpf", "email", "valor_vl"], [["P1", "123", "a@b.com", "10.0"], ["P2", None, "", "5"]])
    assert mascaradas == ["cliente_cpf", "email"]
    assert linhas == [["P1", "•••", "•••", "10.0"], ["P2", None, "", "5"]]


# ----------------------------------------------------------------- configuração

def test_sem_configuracao_orienta_o_operador(capsys, monkeypatch):
    usar(monkeypatch, {})
    assert dados.main(["testar"]) == 1
    err = capsys.readouterr().err
    assert "Acesso a dados" in err and "Não peça credenciais" in err


def test_falta_campo_e_segredo_aponta_o_guia(capsys, monkeypatch):
    usar(monkeypatch, {"dados": {"plataforma": "snowflake", "conexao": {"conta": "org-conta", "usuario": "SQUAD"}}})
    assert dados.main(["testar"]) == 1
    err = capsys.readouterr().err
    assert "dados.conexao.warehouse" in err and "SNOWFLAKE_PRIVATE_KEY" in err and "docs/acesso-dados/snowflake.md" in err


def test_bloco_databricks_antigo_continua_valendo(monkeypatch):
    usar(monkeypatch, {"databricks": {"host": "https://x.cloud.databricks.com", "warehouse_id": "wh1", "leitura": ["vendas"], "escrita": ESCRITA}})
    c = dados.config()
    assert c["plataforma"] == "databricks" and c["conexao"]["warehouse_id"] == "wh1"
    assert c["leitura"] == ["vendas"] and c["escrita"] == ESCRITA


def test_comandos_do_workflow(capsys, monkeypatch):
    usar(monkeypatch, {"dados": {"plataforma": "fabric", "dbt": True}})
    dados.main(["plataforma"])
    dados.main(["usa-dbt"])
    assert capsys.readouterr().out.split() == ["fabric", "sim"]
    usar(monkeypatch, {"plataforma": "dbt", "dados": {"plataforma": ""}})
    dados.main(["plataforma"])
    dados.main(["usa-dbt"])
    assert capsys.readouterr().out.split() == ["nao"]


# ----------------------------------------------------------------- RSA / JWT (biblioteca padrão)

@pytest.fixture(scope="module")
def chave(tmp_path_factory):
    if not shutil.which("openssl"):
        pytest.skip("openssl indisponível")
    d = tmp_path_factory.mktemp("chave")
    priv = d / "rsa_key.p8"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(priv)], check=True, capture_output=True)
    pub = d / "pub.der"
    subprocess.run(["openssl", "pkey", "-in", str(priv), "-pubout", "-outform", "DER", "-out", str(pub)], check=True, capture_output=True)
    return {"pem": priv.read_text(), "pub_der": pub.read_bytes(), "dir": d, "priv": priv}


def test_jwt_assinado_verifica_com_openssl(chave):
    tk = dados.jwt_rs256(chave["pem"], {"sub": "X"})
    cab, corpo, sig = tk.split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
    (chave["dir"] / "msg").write_bytes(f"{cab}.{corpo}".encode())
    (chave["dir"] / "sig").write_bytes(base64.urlsafe_b64decode(pad(sig)))
    (chave["dir"] / "pub.pem").write_bytes(subprocess.run(["openssl", "pkey", "-in", str(chave["priv"]), "-pubout"], check=True, capture_output=True).stdout)
    r = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(chave["dir"] / "pub.pem"), "-signature", str(chave["dir"] / "sig"), str(chave["dir"] / "msg")], capture_output=True, text=True)
    assert "Verified OK" in r.stdout


def test_chave_publica_igual_a_do_openssl(chave):
    n, e, _ = dados._chave_rsa(chave["pem"])
    assert dados.chave_publica_der(n, e) == chave["pub_der"]


def test_chave_com_senha_e_recusada():
    with pytest.raises(dados.Erro, match="senha"):
        dados._chave_rsa("-----BEGIN ENCRYPTED PRIVATE KEY-----\nabc\n-----END ENCRYPTED PRIVATE KEY-----")


# ----------------------------------------------------------------- servidor simulado (todas as plataformas)

class Fake(BaseHTTPRequestHandler):
    pedidos: list = []
    estado: dict = {}
    pub_der: bytes = b""

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _corpo(self) -> str:
        return self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()

    def do_POST(self):
        corpo = self._corpo()
        u = urlparse(self.path)
        Fake.pedidos.append({"path": u.path, "corpo": corpo, "headers": dict(self.headers)})
        # Databricks
        if u.path == "/oidc/v1/token":
            if self.headers.get("Authorization") != "Basic " + base64.b64encode(b"cid:segredo").decode():
                return self._json(401, {"error": "invalid_client", "error_description": "Client authentication failed"})
            return self._json(200, {"access_token": "tk"})
        if u.path == "/api/2.0/sql/statements/":
            j = json.loads(corpo)
            if j["warehouse_id"] != "wh1":
                return self._json(404, {"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "warehouse wh9 does not exist"})
            Fake.estado["s1"] = 0
            return self._json(200, {"statement_id": "s1", "status": {"state": "PENDING"}})
        # Snowflake
        if u.path == "/api/v2/statements":
            tk = (self.headers.get("Authorization") or "").removeprefix("Bearer ")
            assert self.headers.get("X-Snowflake-Authorization-Token-Type") == "KEYPAIR_JWT"
            payload = json.loads(base64.urlsafe_b64decode(tk.split(".")[1] + "=="))
            fp = "SHA256:" + base64.b64encode(hashlib.sha256(Fake.pub_der).digest()).decode()
            if payload["iss"] != f"MINHAORG-CONTA.SQUAD_SVC.{fp}":
                return self._json(401, {"code": "390144", "message": "JWT token is invalid."})
            j = json.loads(corpo)
            if "inexistente" in j["statement"]:
                return self._json(422, {"code": "002003", "message": "Object 'X' does not exist or not authorized."})
            return self._json(202, {"statementHandle": "h1", "message": "Asynchronous execution in progress."})
        # Google
        if u.path == "/token":
            q = parse_qs(corpo)
            assert q["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
            return self._json(200, {"access_token": "gtk"})
        if u.path == "/projects/meu-proj/queries":
            j = json.loads(corpo)
            if "caro" in j["query"]:
                return self._json(400, {"error": {"code": 400, "message": "Query exceeded limit for bytes billed", "errors": [{"reason": "bytesBilledLimitExceeded"}]}})
            return self._json(200, {"jobComplete": False, "jobReference": {"jobId": "j1", "location": "US"}})
        # Entra ID (Fabric)
        if u.path == "/tenant-1/oauth2/v2.0/token":
            q = parse_qs(corpo)
            if q.get("client_secret") != ["fsecret"]:
                return self._json(401, {"error": "invalid_client", "error_description": "AADSTS7000215: Invalid client secret provided."})
            assert q["scope"] == ["https://database.windows.net/.default"]
            return self._json(200, {"access_token": "ftk"})
        self._json(404, {"message": "rota desconhecida " + u.path})

    def do_GET(self):
        u = urlparse(self.path)
        Fake.pedidos.append({"path": u.path, "query": u.query, "headers": dict(self.headers)})
        if u.path == "/api/2.0/sql/statements/s1":
            Fake.estado["s1"] += 1
            if Fake.estado["s1"] < 2:
                return self._json(200, {"statement_id": "s1", "status": {"state": "RUNNING"}})
            return self._json(200, {"statement_id": "s1", "status": {"state": "SUCCEEDED"},
                                    "manifest": {"schema": {"columns": [{"name": "loja_cd"}, {"name": "cliente_email"}]}, "total_row_count": 2},
                                    "result": {"data_array": [["L01", "a@b.com"], ["L02", None]]}})
        if u.path == "/api/v2/statements/h1":
            return self._json(200, {"resultSetMetaData": {"numRows": 3, "rowType": [{"name": "LOJA_CD"}, {"name": "CLIENTE_NOME"}]},
                                    "data": [["L01", "Ana"], ["L02", "Bia"], ["L03", "Caio"]]})
        if u.path == "/projects/meu-proj/queries/j1":
            return self._json(200, {"jobComplete": True, "schema": {"fields": [{"name": "loja_cd"}, {"name": "pedidos_qt"}]},
                                    "rows": [{"f": [{"v": "L01"}, {"v": "10"}]}], "totalRows": "1", "totalBytesProcessed": str(5 * 1024 ** 3)})
        if u.path == "/projects/meu-proj/datasets/vendas/tables/pedidos":
            return self._json(200, {"type": "TABLE", "schema": {"fields": [{"name": "pedido_id"}, {"name": "email"}]}})
        if u.path == "/projects/meu-proj/datasets/vendas/tables/pedidos/data":
            return self._json(200, {"totalRows": "1000", "rows": [{"f": [{"v": "P1"}, {"v": "a@b.com"}]}]})
        self._json(404, {"message": "rota desconhecida " + u.path})


@pytest.fixture
def servidor():
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    Fake.pedidos.clear()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


# ---- Databricks

@pytest.fixture
def databricks(servidor, monkeypatch):
    usar(monkeypatch, {"dados": {"plataforma": "databricks", "conexao": {"host": servidor, "warehouse_id": "wh1"}, "escrita": ESCRITA, "leitura": ["vendas"]}})
    monkeypatch.setenv("DATABRICKS_CLIENT_ID", "cid")
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "segredo")
    return servidor


def test_databricks_consulta_ponta_a_ponta(databricks, capsys):
    assert dados.main(["sql", "SELECT loja_cd, cliente_email FROM vendas.silver.clientes", "--linhas", "500"]) == 0
    out = capsys.readouterr().out
    assert "| L01 | ••• |" in out and "a@b.com" not in out and "colunas mascaradas" in out
    pedido = json.loads(next(p for p in Fake.pedidos if p["path"] == "/api/2.0/sql/statements/")["corpo"])
    assert pedido["row_limit"] == dados.LIMITE_MAXIMO and pedido["disposition"] == "INLINE"


def test_databricks_credenciais_erradas(databricks, monkeypatch, capsys):
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "errado")
    assert dados.main(["testar"]) == 1
    assert "Credenciais recusadas" in capsys.readouterr().err


def test_databricks_warehouse_inexistente(databricks, monkeypatch, capsys):
    usar(monkeypatch, {"dados": {"plataforma": "databricks", "conexao": {"host": databricks, "warehouse_id": "wh9"}}})
    assert dados.main(["testar"]) == 1
    assert "warehouse não encontrado" in capsys.readouterr().err


def test_escrita_fora_da_sandbox_nem_chega_a_plataforma(databricks, capsys):
    assert dados.main(["sql", "DROP TABLE producao.gold.receita"]) == 1
    assert Fake.pedidos == []


def test_dbx_py_continua_funcionando(databricks):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dbx.py"), "ajuda"], capture_output=True, text=True)
    assert r.returncode == 0 and "dados.py" in r.stdout


# ---- Snowflake

@pytest.fixture
def snowflake(servidor, chave, monkeypatch):
    Fake.pub_der = chave["pub_der"]
    usar(monkeypatch, {"dados": {"plataforma": "snowflake", "conexao": {"conta": "minhaorg-conta", "usuario": "squad_svc", "warehouse": "squad_wh", "papel": "squad_role"}, "escrita": ESCRITA}})
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY", chave["pem"])
    monkeypatch.setenv("DADOS_URL_BASE", servidor)
    return servidor


def test_snowflake_jwt_assincrono_e_mascara(snowflake, capsys):
    assert dados.main(["sql", "SELECT loja_cd, cliente_nome FROM vendas.silver.clientes", "--linhas", "2"]) == 0
    out = capsys.readouterr().out
    assert "| L01 | ••• |" in out and "Ana" not in out and "resultado limitado a 2" in out
    corpo = json.loads(next(p for p in Fake.pedidos if p["path"] == "/api/v2/statements")["corpo"])
    assert corpo["warehouse"] == "SQUAD_WH" and corpo["role"] == "SQUAD_ROLE"
    assert corpo["parameters"]["QUERY_TAG"] == dados.TAG and corpo["parameters"]["ROWS_PER_RESULTSET"] == "3"


def test_snowflake_chave_errada(snowflake, monkeypatch, capsys):
    usar(monkeypatch, {"dados": {"plataforma": "snowflake", "conexao": {"conta": "minhaorg-conta", "usuario": "outro", "warehouse": "w"}}})
    assert dados.main(["testar"]) == 1
    assert "Chave recusada" in capsys.readouterr().err


def test_snowflake_sem_permissao(snowflake, capsys):
    assert dados.main(["sql", "SELECT * FROM inexistente.x.y"]) == 1
    assert "sem permissão" in capsys.readouterr().err


# ---- BigQuery

@pytest.fixture
def bigquery(servidor, chave, monkeypatch):
    sa = {"type": "service_account", "client_email": "squad@meu-proj.iam.gserviceaccount.com", "private_key": chave["pem"], "token_uri": f"{servidor}/token"}
    usar(monkeypatch, {"dados": {"plataforma": "bigquery", "conexao": {"projeto": "meu-proj", "local": "US", "max_gb": "20"}, "escrita": "meu-proj.sandbox"}})
    monkeypatch.setenv("GCP_SA_KEY", json.dumps(sa))
    monkeypatch.setenv("DADOS_URL_BASE", servidor)
    return servidor


def test_bigquery_consulta_com_limite_de_bytes(bigquery, capsys):
    assert dados.main(["sql", "SELECT loja_cd, COUNT(*) AS pedidos_qt FROM `meu-proj.vendas.pedidos` GROUP BY 1"]) == 0
    out = capsys.readouterr().out
    assert "| L01 | 10 |" in out and "5.00 GB processados" in out
    corpo = json.loads(next(p for p in Fake.pedidos if p["path"] == "/projects/meu-proj/queries")["corpo"])
    assert corpo["maximumBytesBilled"] == str(20 * 1024 ** 3) and corpo["useLegacySql"] is False
    assert corpo["labels"] == {"origem": dados.TAG} and corpo["location"] == "US"


def test_bigquery_amostra_sem_custo(bigquery, capsys):
    assert dados.main(["amostra", "meu-proj.vendas.pedidos", "--linhas", "5"]) == 0
    out = capsys.readouterr().out
    assert "| P1 | ••• |" in out and "sem custo" in out
    assert not any(p["path"].endswith("/queries") for p in Fake.pedidos)


def test_bigquery_consulta_cara_e_barrada(bigquery, capsys):
    assert dados.main(["sql", "SELECT * FROM caro.x.y"]) == 1
    assert "limite de 20" in capsys.readouterr().err


# ---- Fabric

class FakeCursor:
    def __init__(self, log):
        self.log, self.description = log, None

    def execute(self, sql):
        self.log.append(sql)
        self.description = [("loja_cd",), ("cliente_email",)]

    def fetchmany(self, n):
        return [("L01", "a@b.com"), ("L02", "c@d.com"), ("L03", None)][:n]


class FakeConn:
    def __init__(self, log):
        self.log, self.timeout = log, 0

    def cursor(self):
        return FakeCursor(self.log)

    def close(self):
        pass


@pytest.fixture
def fabric(servidor, monkeypatch):
    log: list = []
    mod = types.ModuleType("pyodbc")
    mod.Error = Exception
    mod.drivers = lambda: ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server"]

    def connect(conn_str, attrs_before=None, autocommit=False, timeout=0):
        log.append({"conn": conn_str, "attrs": attrs_before, "autocommit": autocommit})
        return FakeConn(log)

    mod.connect = connect
    monkeypatch.setitem(sys.modules, "pyodbc", mod)
    usar(monkeypatch, {"dados": {"plataforma": "fabric", "conexao": {"servidor": "abc.datawarehouse.fabric.microsoft.com", "banco": "squad_dev", "tenant_id": "tenant-1"}, "escrita": ESCRITA}})
    monkeypatch.setenv("FABRIC_CLIENT_ID", "fid")
    monkeypatch.setenv("FABRIC_CLIENT_SECRET", "fsecret")
    monkeypatch.setenv("DADOS_URL_BASE", servidor)
    return log


def test_fabric_token_entra_e_consulta(fabric, capsys):
    assert dados.main(["amostra", "vendas.dbo.clientes", "--linhas", "2"]) == 0
    out = capsys.readouterr().out
    assert "| L01 | ••• |" in out and "resultado limitado a 2" in out
    conexao = fabric[0]
    assert "Driver={ODBC Driver 18 for SQL Server}" in conexao["conn"] and "Server=tcp:abc.datawarehouse.fabric.microsoft.com,1433" in conexao["conn"]
    tk = "ftk".encode("utf-16-le")
    assert conexao["attrs"][1256] == len(tk).to_bytes(4, "little") + tk
    assert fabric[1] == "SELECT TOP 2 * FROM [vendas].[dbo].[clientes]"


def test_fabric_secret_errado(fabric, monkeypatch, capsys):
    monkeypatch.setenv("FABRIC_CLIENT_SECRET", "errado")
    assert dados.main(["testar"]) == 1
    assert "Client secret inválido" in capsys.readouterr().err


def test_fabric_sem_driver(fabric, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "pyodbc", None)
    assert dados.main(["testar"]) == 1
    assert "Driver do Fabric ausente" in capsys.readouterr().err


# ----------------------------------------------------------------- dbt

@pytest.mark.parametrize("raiz, segredos, tipo", [
    ({"plataforma": "databricks", "conexao": {"host": "https://x.cloud.databricks.com", "warehouse_id": "wh1"}}, {"DATABRICKS_CLIENT_ID": "a", "DATABRICKS_CLIENT_SECRET": "b"}, "databricks"),
    ({"plataforma": "snowflake", "conexao": {"conta": "org-conta", "usuario": "u", "warehouse": "w"}}, {"SNOWFLAKE_PRIVATE_KEY": "pem"}, "snowflake"),
    ({"plataforma": "fabric", "conexao": {"servidor": "s.datawarehouse.fabric.microsoft.com", "banco": "squad_dev", "tenant_id": "t"}}, {"FABRIC_CLIENT_ID": "a", "FABRIC_CLIENT_SECRET": "b"}, "fabric"),
])
def test_dbt_profile_sem_segredos_no_arquivo(raiz, segredos, tipo, monkeypatch, tmp_path):
    usar(monkeypatch, {"dados": {**raiz, "escrita": ESCRITA, "dbt": True}})
    for k, v in segredos.items():
        monkeypatch.setenv(k, v)
    assert dados.main(["dbt-profile", "--saida", str(tmp_path / "dbt")]) == 0
    texto = (tmp_path / "dbt" / "profiles.yml").read_text()
    perfil = json.loads(texto.split("\n", 1)[1])["squad"]["outputs"]["sandbox"]
    assert perfil["type"] == tipo
    assert perfil.get("schema") == "agentes"
    for v in segredos.values():
        assert f'"{v}"' not in texto, "segredos ficam em env_var(), não no arquivo"


def test_dbt_profile_bigquery_guarda_chave_fora_do_repo(bigquery, tmp_path):
    assert dados.main(["dbt-profile", "--saida", str(tmp_path / "dbt")]) == 0
    perfil = json.loads((tmp_path / "dbt" / "profiles.yml").read_text().split("\n", 1)[1])["squad"]["outputs"]["sandbox"]
    assert perfil["dataset"] == "sandbox" and Path(perfil["keyfile"]).parent == tmp_path / "dbt"
    assert oct(Path(perfil["keyfile"]).stat().st_mode)[-3:] == "600"


def test_dbt_profile_nao_vai_para_o_repositorio(databricks, capsys):
    assert dados.main(["dbt-profile", "--saida", str(ROOT / "tmp-dbt")]) == 1
    assert "dentro do repositório" in capsys.readouterr().err
