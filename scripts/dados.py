#!/usr/bin/env python3
"""Acesso dos agentes aos dados da squad, com travas de segurança.

Plataformas: Databricks, Snowflake, BigQuery e Microsoft Fabric (Warehouse/Lakehouse).

A segurança de verdade é da plataforma: a identidade da squad (service principal,
usuário de serviço ou service account) só tem leitura nas fontes e escrita na
sandbox. Este script acrescenta travas:
  - uma instrução por vez; GRANT/REVOKE/EXECUTE/CALL e afins sempre bloqueados
  - escrita (CREATE/INSERT/MERGE/…) só em objetos da sandbox (dados.escrita)
  - limite de linhas devolvidas (e de bytes processados no BigQuery)
  - colunas com cara de dado pessoal mascaradas na saída

Uso:
  python scripts/dados.py status                       # configuração atual (sem segredos)
  python scripts/dados.py testar                       # autentica e roda uma consulta mínima
  python scripts/dados.py catalogo [banco[.schema]]    # tabelas e colunas visíveis
  python scripts/dados.py amostra <banco.schema.tabela> [--linhas 20]
  python scripts/dados.py sql "<instrução>" [--linhas 50]
  python scripts/dados.py dbt-profile --saida <pasta>  # gera profiles.yml (CI; fora do repositório)

"banco" é o primeiro nível do nome: catálogo (Databricks), database (Snowflake),
projeto (BigQuery) ou warehouse/lakehouse (Fabric). "schema" é o dataset no BigQuery.

Configuração: bloco "dados" do .squad/squad.yaml (plataforma, conexao, leitura, escrita, dbt).
Segredos (GitHub Actions), conforme a plataforma:
  databricks  DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET
  snowflake   SNOWFLAKE_PRIVATE_KEY (chave privada PKCS#8 em PEM, sem senha)
  bigquery    GCP_SA_KEY (JSON da service account)
  fabric      FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200
TIMEOUT_S = 300
TAG = "squad-agentica"
CONSOLE = "Squad Console → Configuração → Acesso a dados"

RE_PII = re.compile(
    r"(cpf|cnpj|rg|email|e_mail|telefone|celular|fone|whats|nome|name|endereco|logradouro|cep|"
    r"nascimento|birth|senha|password|token|cartao|card|conta|iban|pis|cns|passaporte|ip_?addr)",
    re.I,
)
LEITURA = ("SELECT", "WITH", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "VALUES", "LIST")
ESCRITA = ("CREATE", "INSERT", "MERGE", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "REPLACE", "COPY", "OPTIMIZE", "VACUUM", "COMMENT")
VERBOS_ESCRITA = ("INSERT", "MERGE", "DELETE", "UPDATE", "DROP", "ALTER", "TRUNCATE", "CREATE", "INTO")
PROIBIDOS = ("GRANT", "REVOKE", "DENY", "SET OWNER", "USE CATALOG", "CREATE CATALOG", "DROP CATALOG", "CREATE CONNECTION",
             "CREATE EXTERNAL", "CREATE STORAGE CREDENTIAL", "CREATE SHARE", "CREATE RECIPIENT", "MSCK", "REFRESH FOREIGN",
             "EXEC", "EXECUTE", "CALL", "IMPERSONATE", "OPENROWSET", "OPENDATASOURCE", "CREATE USER", "CREATE ROLE",
             "CREATE LOGIN", "CREATE INTEGRATION", "CREATE STAGE", "EXPORT DATA")
NOME = r"[`\"\[\]\w.\-]+"


class Erro(Exception):
    pass


@dataclass
class Resultado:
    colunas: list[str]
    linhas: list[list]
    truncado: bool = False
    extra: list[str] = field(default_factory=list)


# ----------------------------------------------------------------- configuração

def _raiz() -> dict:
    caminho = ROOT / ".squad" / "squad.yaml"
    if not caminho.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}


def _lista(v) -> list[str]:
    if isinstance(v, str):
        v = v.split(",")
    return [str(x).strip().strip("`").lower() for x in (v or []) if str(x).strip()]


def config() -> dict:
    raiz = _raiz()
    d = raiz.get("dados") or {}
    legado = raiz.get("databricks") or {}  # squads configuradas antes do bloco "dados"
    plataforma = str(os.environ.get("DADOS_PLATAFORMA") or d.get("plataforma") or "").strip().lower()
    conexao = {k: str(v if v is not None else "").strip() for k, v in (d.get("conexao") or {}).items()}
    if not plataforma and (legado.get("host") or os.environ.get("DATABRICKS_HOST")):
        plataforma = "databricks"
    if plataforma == "databricks":
        conexao.setdefault("host", str(legado.get("host") or ""))
        conexao.setdefault("warehouse_id", str(legado.get("warehouse_id") or ""))
        if os.environ.get("DATABRICKS_HOST"):
            conexao["host"] = os.environ["DATABRICKS_HOST"]
        if os.environ.get("DATABRICKS_WAREHOUSE_ID"):
            conexao["warehouse_id"] = os.environ["DATABRICKS_WAREHOUSE_ID"]
    leitura = _lista(os.environ.get("DADOS_LEITURA") or os.environ.get("DATABRICKS_LEITURA") or d.get("leitura") or legado.get("leitura"))
    escrita = str(os.environ.get("DADOS_ESCRITA") or os.environ.get("DATABRICKS_ESCRITA") or d.get("escrita") or legado.get("escrita") or "")
    return {
        "plataforma": plataforma,
        "conexao": conexao,
        "leitura": leitura,
        "escrita": escrita.strip().strip("`").lower(),
        "dbt": str(d.get("dbt") or "").lower() in ("true", "sim", "1", "yes"),
    }


def _segredo(nome: str) -> str:
    return os.environ.get(nome, "").strip()


# ----------------------------------------------------------------- travas

def _sem_comentarios_e_literais(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"'(?:[^'\\]|\\.|'')*'", "''", sql)
    return sql


def _limpar_nome(n: str) -> str:
    return re.sub(r"[`\"\[\]]", "", n).lower()


def _alvos_de_escrita(sql: str) -> list[str]:
    """Objetos que a instrução cria/altera (nomes sem aspas, crases ou colchetes)."""
    padroes = [
        rf"\b(?:CREATE|REPLACE)\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?(?:TEMPORARY\s+|TEMP\s+|TRANSIENT\s+)?(?:MATERIALIZED\s+)?(?:TABLE|VIEW|SCHEMA|DATABASE|FUNCTION|VOLUME)\s+(?:IF\s+NOT\s+EXISTS\s+)?({NOME})",
        rf"\bINSERT\s+(?:INTO|OVERWRITE)\s+(?:TABLE\s+)?({NOME})",
        rf"\bINTO\s+({NOME})",
        rf"\bMERGE\s+INTO\s+({NOME})",
        rf"^\s*UPDATE\s+({NOME})",
        rf"\bDELETE\s+FROM\s+({NOME})",
        rf"\bDROP\s+(?:TABLE|VIEW|SCHEMA|DATABASE|FUNCTION|VOLUME|MATERIALIZED\s+VIEW)\s+(?:IF\s+EXISTS\s+)?({NOME})",
        rf"\bALTER\s+(?:TABLE|VIEW|SCHEMA|DATABASE)\s+({NOME})",
        rf"\bTRUNCATE\s+TABLE\s+({NOME})",
        rf"\bCOPY\s+INTO\s+({NOME})",
        rf"\b(?:OPTIMIZE|VACUUM)\s+({NOME})",
        rf"\bCOMMENT\s+ON\s+(?:TABLE|COLUMN|SCHEMA|VIEW)\s+({NOME})",
    ]
    alvos: list[str] = []
    for p in padroes:
        for m in re.finditer(p, sql, re.I):
            a = _limpar_nome(m.group(1))
            if a not in alvos:
                alvos.append(a)
    return alvos


def validar_sql(sql: str, escrita: str) -> str:
    """Devolve 'leitura' ou 'escrita'; levanta Erro se a instrução não for permitida."""
    limpo = _sem_comentarios_e_literais(sql).strip().rstrip(";").strip()
    if not limpo:
        raise Erro("Instrução vazia.")
    if ";" in limpo:
        raise Erro("Envie uma instrução por vez (sem ';' no meio).")
    upper = re.sub(r"\s+", " ", re.sub(r'"[^"]*"', '""', limpo).upper())
    for p in PROIBIDOS:
        if re.search(rf"\b{p}\b", upper):
            raise Erro(f"'{p}' não é permitido aos agentes. Permissões e rotinas são administradas pelo Operador na plataforma.")
    primeira = upper.split(" ", 1)[0]
    if primeira in LEITURA and not any(re.search(rf"\b{k}\b", upper) for k in VERBOS_ESCRITA):
        return "leitura"
    if primeira in ESCRITA or primeira in LEITURA:
        if not escrita:
            raise Erro("Escrita bloqueada: não há sandbox configurada (dados.escrita em .squad/squad.yaml).")
        alvos = _alvos_de_escrita(limpo)
        if not alvos:
            raise Erro("Não consegui identificar o objeto alterado. Use nomes completos: banco.schema.tabela.")
        for a in alvos:
            partes = a.split(".")
            if len(partes) < 3 and not (len(partes) == 2 and a == escrita):
                raise Erro(f"Use o nome completo banco.schema.objeto para escrever (recebi '{a}').")
            if ".".join(partes[:2]) != escrita:
                raise Erro(f"Escrita só é permitida em {escrita}. '{a}' está fora da sandbox da squad.")
        return "escrita"
    raise Erro(f"Tipo de instrução não permitido: {primeira}.")


def mascarar(colunas: list[str], linhas: list[list]) -> tuple[list[list], list[str]]:
    sensiveis = [i for i, c in enumerate(colunas) if RE_PII.search(c or "")]
    if not sensiveis:
        return linhas, []
    out = []
    for l in linhas:
        l = list(l)
        for i in sensiveis:
            if i < len(l) and l[i] not in (None, ""):
                l[i] = "•••"
        out.append(l)
    return out, [colunas[i] for i in sensiveis]


# ----------------------------------------------------------------- HTTP e RSA (só biblioteca padrão)

def _req(url: str, *, data: bytes | None = None, headers: dict | None = None, method: str | None = None,
         explicar=None, onde: str = "a plataforma") -> tuple[int, dict]:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "squad-agentica/1.0", **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            corpo = r.read().decode("utf-8") or "{}"
            return r.status, json.loads(corpo)
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")
        try:
            j = json.loads(corpo)
        except json.JSONDecodeError:
            j = {"message": corpo[:300]}
        raise Erro((explicar or _explicar_generico)(e.code, j)) from None
    except urllib.error.URLError as e:
        raise Erro(f"Não foi possível conectar a {onde} ({e.reason}). Confira o endereço em dados.conexao.") from None


def _explicar_generico(status: int, j: dict) -> str:
    return f"HTTP {status}: {j.get('message') or j.get('error_description') or j.get('error') or j}"


def _der(buf: bytes, i: int) -> tuple[int, bytes, int]:
    tag = buf[i]
    tam = buf[i + 1]
    i += 2
    if tam & 0x80:
        n = tam & 0x7F
        tam = int.from_bytes(buf[i:i + n], "big")
        i += n
    return tag, buf[i:i + tam], i + tam


def _der_seq(buf: bytes) -> list[tuple[int, bytes]]:
    out, i = [], 0
    while i < len(buf):
        tag, val, i = _der(buf, i)
        out.append((tag, val))
    return out


def _chave_rsa(pem: str) -> tuple[int, int, int]:
    """(n, e, d) de uma chave privada RSA em PEM (PKCS#8 ou PKCS#1, sem senha)."""
    pem = pem.strip().replace("\\n", "\n")
    if "ENCRYPTED" in pem:
        raise Erro("A chave privada está protegida por senha. Gere uma versão sem senha (PKCS#8, -nocrypt).")
    m = re.search(r"-----BEGIN ([A-Z ]+)-----(.+?)-----END \1-----", pem, re.S)
    if not m:
        raise Erro("Chave privada inválida: esperado um PEM que começa com -----BEGIN PRIVATE KEY-----.")
    der = base64.b64decode("".join(m.group(2).split()))
    _, seq, _ = _der(der, 0)
    itens = _der_seq(seq)
    if m.group(1) == "PRIVATE KEY":  # PKCS#8: version, algoritmo, OCTET STRING(RSAPrivateKey)
        _, seq, _ = _der(itens[2][1], 0)
        itens = _der_seq(seq)
    ints = [int.from_bytes(v, "big") for t, v in itens if t == 0x02]
    if len(ints) < 4:
        raise Erro("Chave privada inválida: não é uma chave RSA.")
    return ints[1], ints[2], ints[3]


def _der_int(x: int) -> bytes:
    b = x.to_bytes((x.bit_length() + 8) // 8 or 1, "big")
    return _der_tlv(0x02, b)


def _der_tlv(tag: int, val: bytes) -> bytes:
    n = len(val)
    if n < 0x80:
        return bytes([tag, n]) + val
    nb = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(nb)]) + nb + val


def chave_publica_der(n: int, e: int) -> bytes:
    rsa_pub = _der_tlv(0x30, _der_int(n) + _der_int(e))
    alg = _der_tlv(0x30, bytes.fromhex("06092a864886f70d010101") + b"\x05\x00")
    return _der_tlv(0x30, alg + _der_tlv(0x03, b"\x00" + rsa_pub))


def assinar_rs256(n: int, d: int, msg: bytes) -> bytes:
    k = (n.bit_length() + 7) // 8
    t = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(msg).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(k, "big")


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt_rs256(pem: str, payload: dict) -> str:
    n, _e, d = _chave_rsa(pem)
    cab = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    corpo = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    assinatura = assinar_rs256(n, d, f"{cab}.{corpo}".encode())
    return f"{cab}.{corpo}.{_b64url(assinatura)}"


def _host(v: str) -> str:
    v = v.strip()
    if not v:
        return ""
    if not re.match(r"^https?://", v, re.I):
        v = "https://" + v
    p = urllib.parse.urlparse(v)
    return f"{p.scheme}://{p.netloc}"


# ----------------------------------------------------------------- plataformas

class Plataforma:
    nome = ""
    rotulo = ""
    campos: dict[str, str] = {}          # campo de dados.conexao → descrição (obrigatórios)
    segredos: tuple[str, ...] = ()
    teste = "SELECT 1"
    guia = "docs/acesso-dados.md"

    def __init__(self, c: dict):
        self.c = c
        self.cx = c["conexao"]

    def faltando(self) -> list[str]:
        f = [f"dados.conexao.{k} ({v}) em .squad/squad.yaml" for k, v in self.campos.items() if not self.cx.get(k)]
        f += [f"segredo {s}" for s in self.segredos if not _segredo(s)]
        return f

    def q(self, partes: list[str]) -> str:
        return ".".join(f"`{p}`" for p in partes)

    def sql_amostra(self, partes: list[str], n: int) -> str:
        return f"SELECT * FROM {self.q(partes)} LIMIT {n}"

    def amostra(self, partes: list[str], n: int) -> Resultado:
        return self.executar(self.sql_amostra(partes, n), n)

    def sql_tabelas(self, banco: str, schema: str | None) -> str:
        filtro = f" AND lower(table_schema) = '{schema}'" if schema else ""
        return (f"SELECT table_schema, table_name, table_type FROM {self.q([banco])}.information_schema.tables "
                f"WHERE lower(table_schema) <> 'information_schema'{filtro} ORDER BY 1, 2")

    def sql_colunas(self, banco: str, schema: str) -> str:
        return (f"SELECT table_name, column_name, data_type FROM {self.q([banco])}.information_schema.columns "
                f"WHERE lower(table_schema) = '{schema}' ORDER BY table_name, ordinal_position")

    def sql_bancos(self) -> str:
        return "SHOW CATALOGS"

    def executar(self, sql: str, linhas: int) -> Resultado:  # pragma: no cover - abstrato
        raise NotImplementedError

    def dbt_profile(self, schema_alvo: str, pasta: Path) -> dict:  # pragma: no cover - abstrato
        raise NotImplementedError


class Databricks(Plataforma):
    nome, rotulo = "databricks", "Databricks"
    campos = {"host": "URL do workspace", "warehouse_id": "ID do SQL warehouse"}
    segredos = ("DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET")
    teste = "SELECT current_user() AS usuario, current_catalog() AS catalogo_padrao"
    guia = "docs/acesso-dados/databricks.md"

    def _explicar(self, status: int, j: dict) -> str:
        code = str(j.get("error_code") or j.get("error") or "")
        msg = str(j.get("message") or j.get("error_description") or j)
        base = f"HTTP {status} {code}: {msg}".strip()
        if status == 401 or "invalid_client" in code:
            return f"Credenciais recusadas: confira DATABRICKS_CLIENT_ID e DATABRICKS_CLIENT_SECRET (o secret expira). [{base}]"
        if status == 403 and "warehouse" in msg.lower():
            return f"O service principal não tem 'Can use' no SQL warehouse. [{base}]"
        if status == 403:
            return f"Permissão negada no Databricks. [{base}]"
        if status == 404 and "warehouse" in msg.lower():
            return f"SQL warehouse não encontrado: confira dados.conexao.warehouse_id. [{base}]"
        return base

    def _token(self) -> str:
        basic = base64.b64encode(f"{_segredo('DATABRICKS_CLIENT_ID')}:{_segredo('DATABRICKS_CLIENT_SECRET')}".encode()).decode()
        _, r = _req(
            f"{_host(self.cx['host'])}/oidc/v1/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"}).encode(),
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST", explicar=self._explicar, onde="o Databricks",
        )
        if not r.get("access_token"):
            raise Erro("O Databricks não devolveu token de acesso.")
        return r["access_token"]

    def executar(self, sql: str, linhas: int) -> Resultado:
        host = _host(self.cx["host"])
        h = {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}
        corpo = {
            "warehouse_id": self.cx["warehouse_id"], "statement": sql, "wait_timeout": "50s",
            "on_wait_timeout": "CONTINUE", "disposition": "INLINE", "format": "JSON_ARRAY",
            "row_limit": linhas, "query_tags": [{"key": "origem", "value": TAG}],
        }
        kw = {"headers": h, "explicar": self._explicar, "onde": "o Databricks"}
        _, r = _req(f"{host}/api/2.0/sql/statements/", data=json.dumps(corpo).encode(), method="POST", **kw)
        inicio = time.time()
        while (r.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
            if time.time() - inicio > TIMEOUT_S:
                _req(f"{host}/api/2.0/sql/statements/{r['statement_id']}/cancel", data=b"", method="POST", **kw)
                raise Erro(f"A consulta passou de {TIMEOUT_S}s e foi cancelada. Reduza o volume (filtros, LIMIT).")
            time.sleep(3)
            _, r = _req(f"{host}/api/2.0/sql/statements/{r['statement_id']}", **kw)
        estado = (r.get("status") or {}).get("state")
        if estado != "SUCCEEDED":
            err = (r.get("status") or {}).get("error") or {}
            raise Erro(f"A consulta terminou como {estado}: {err.get('error_code', '')} {err.get('message', '')}".strip())
        man = r.get("manifest") or {}
        cols = [x["name"] for x in (man.get("schema") or {}).get("columns", [])]
        dados = (r.get("result") or {}).get("data_array") or []
        total = man.get("total_row_count")
        return Resultado(cols, dados, bool(man.get("truncated") or (total and total > len(dados))))

    def dbt_profile(self, schema_alvo: str, pasta: Path) -> dict:
        cat, sch = schema_alvo.split(".")
        return {
            "type": "databricks", "host": _host(self.cx["host"]).split("://", 1)[1],
            "http_path": f"/sql/1.0/warehouses/{self.cx['warehouse_id']}", "catalog": cat, "schema": sch,
            "auth_type": "oauth", "client_id": "{{ env_var('DATABRICKS_CLIENT_ID') }}",
            "client_secret": "{{ env_var('DATABRICKS_CLIENT_SECRET') }}", "threads": 4,
        }


class Snowflake(Plataforma):
    nome, rotulo = "snowflake", "Snowflake"
    campos = {"conta": "identificador da conta, ex.: minhaorg-minhaconta", "usuario": "usuário de serviço", "warehouse": "virtual warehouse"}
    segredos = ("SNOWFLAKE_PRIVATE_KEY",)
    teste = "SELECT CURRENT_USER() AS usuario, CURRENT_ROLE() AS papel, CURRENT_WAREHOUSE() AS warehouse"
    guia = "docs/acesso-dados/snowflake.md"

    def q(self, partes: list[str]) -> str:
        return ".".join(partes)  # nomes já validados (\w); sem aspas = sem diferença de maiúsculas

    def sql_bancos(self) -> str:
        return "SHOW DATABASES"

    def _conta(self) -> str:
        c = self.cx["conta"].strip().lower()
        c = re.sub(r"^https?://", "", c).split("/")[0].replace(".snowflakecomputing.com", "")
        return c

    def url(self) -> str:
        return os.environ.get("DADOS_URL_BASE") or f"https://{self._conta().replace('_', '-')}.snowflakecomputing.com"

    def jwt(self) -> str:
        pem = _segredo("SNOWFLAKE_PRIVATE_KEY")
        n, e, _ = _chave_rsa(pem)
        fp = "SHA256:" + base64.b64encode(hashlib.sha256(chave_publica_der(n, e)).digest()).decode()
        conta = self._conta().upper()
        conta = conta.split(".")[0] if "." in conta else conta
        usuario = self.cx["usuario"].upper()
        agora = int(time.time())
        return jwt_rs256(pem, {"iss": f"{conta}.{usuario}.{fp}", "sub": f"{conta}.{usuario}", "iat": agora, "exp": agora + 3540})

    def _explicar(self, status: int, j: dict) -> str:
        msg = str(j.get("message") or j)
        base = f"HTTP {status} {j.get('code', '')}: {msg}".strip()
        if status == 401:
            return ("Chave recusada pelo Snowflake: confira conta, usuário e se a chave pública foi registrada "
                    f"(ALTER USER ... SET RSA_PUBLIC_KEY). [{base}]")
        if status == 422 and re.search(r"does not exist or not authorized", msg, re.I):
            return f"Objeto inexistente ou sem permissão para o papel da squad (GRANT USAGE/SELECT). [{base}]"
        if status == 422 and re.search(r"warehouse", msg, re.I):
            return f"Problema com o warehouse: confira dados.conexao.warehouse e o GRANT USAGE ON WAREHOUSE ao papel. [{base}]"
        return base

    def executar(self, sql: str, linhas: int) -> Resultado:
        h = {"Authorization": f"Bearer {self.jwt()}", "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
             "Content-Type": "application/json", "Accept": "application/json"}
        corpo = {"statement": sql, "timeout": TIMEOUT_S, "warehouse": self.cx["warehouse"].upper(),
                 "parameters": {"QUERY_TAG": TAG, "ROWS_PER_RESULTSET": str(linhas + 1)}}
        if self.cx.get("papel"):
            corpo["role"] = self.cx["papel"].upper()
        kw = {"headers": h, "explicar": self._explicar, "onde": "o Snowflake"}
        st, r = _req(f"{self.url()}/api/v2/statements?requestId={uuid.uuid4()}", data=json.dumps(corpo).encode(), method="POST", **kw)
        inicio = time.time()
        while st == 202:
            if time.time() - inicio > TIMEOUT_S:
                _req(f"{self.url()}/api/v2/statements/{r['statementHandle']}/cancel", data=b"{}", method="POST", **kw)
                raise Erro(f"A consulta passou de {TIMEOUT_S}s e foi cancelada. Reduza o volume (filtros, LIMIT).")
            time.sleep(3)
            st, r = _req(f"{self.url()}/api/v2/statements/{r['statementHandle']}", **kw)
        meta = r.get("resultSetMetaData") or {}
        cols = [x.get("name", "") for x in meta.get("rowType") or []]
        dados = r.get("data") or []
        total = int(meta.get("numRows") or len(dados))
        return Resultado(cols, dados[:linhas], total > linhas)

    def dbt_profile(self, schema_alvo: str, pasta: Path) -> dict:
        db, sch = schema_alvo.split(".")
        p = {"type": "snowflake", "account": self._conta(), "user": self.cx["usuario"], "warehouse": self.cx["warehouse"],
             "database": db, "schema": sch, "private_key": "{{ env_var('SNOWFLAKE_PRIVATE_KEY') }}", "threads": 4,
             "query_tag": TAG}
        if self.cx.get("papel"):
            p["role"] = self.cx["papel"]
        return p


class BigQuery(Plataforma):
    nome, rotulo = "bigquery", "BigQuery"
    campos = {"projeto": "projeto que executa (e paga) as consultas"}
    segredos = ("GCP_SA_KEY",)
    teste = "SELECT SESSION_USER() AS usuario"
    guia = "docs/acesso-dados/bigquery.md"
    API = "https://bigquery.googleapis.com/bigquery/v2"

    def api(self) -> str:
        return os.environ.get("DADOS_URL_BASE") or self.API

    def regiao(self) -> str:
        return "region-" + (self.cx.get("local") or "us").lower()

    def sql_bancos(self) -> str:
        return f"SELECT schema_name AS dataset FROM {self.q([self.cx['projeto'], self.regiao()])}.INFORMATION_SCHEMA.SCHEMATA ORDER BY 1"

    def sql_tabelas(self, banco: str, schema: str | None) -> str:
        if schema:
            return f"SELECT table_schema, table_name, table_type FROM {self.q([banco, schema])}.INFORMATION_SCHEMA.TABLES ORDER BY 1, 2"
        return f"SELECT table_schema, table_name, table_type FROM {self.q([banco, self.regiao()])}.INFORMATION_SCHEMA.TABLES ORDER BY 1, 2"

    def sql_colunas(self, banco: str, schema: str) -> str:
        return (f"SELECT table_name, column_name, data_type FROM {self.q([banco, schema])}.INFORMATION_SCHEMA.COLUMNS "
                "ORDER BY table_name, ordinal_position")

    def _chave(self) -> dict:
        bruto = _segredo("GCP_SA_KEY")
        if bruto and not bruto.startswith("{"):
            try:
                bruto = base64.b64decode(bruto).decode()
            except Exception:
                pass
        try:
            k = json.loads(bruto)
        except json.JSONDecodeError:
            raise Erro("GCP_SA_KEY não é o JSON da service account.") from None
        if k.get("type") != "service_account" or not k.get("private_key") or not k.get("client_email"):
            raise Erro("GCP_SA_KEY precisa ser a chave JSON de uma service account (type: service_account).")
        return k

    def _explicar(self, status: int, j: dict) -> str:
        err = j.get("error") if isinstance(j.get("error"), dict) else {}
        msg = str(err.get("message") or j.get("error_description") or j.get("error") or j)
        motivo = ",".join(str(e.get("reason")) for e in err.get("errors") or [] if e.get("reason"))
        base = f"HTTP {status} {motivo}: {msg}".strip()
        if status in (400, 401) and (j.get("error") == "invalid_grant" or "invalid_grant" in msg):
            return f"Chave da service account recusada (revogada ou relógio fora de sincronia). [{base}]"
        if "bytesBilledLimitExceeded" in motivo:
            return (f"A consulta processaria mais que o limite de {self._max_gb()} GB. Filtre por partição/colunas "
                    f"ou peça ao Operador para ajustar dados.conexao.max_gb. [{base}]")
        if status == 403:
            return f"Sem permissão no BigQuery (a service account precisa de Data Viewer nas fontes e Job User no projeto). [{base}]"
        if status == 404:
            return f"Projeto, dataset ou tabela não encontrado (ou invisível para a service account). [{base}]"
        return base

    def _max_gb(self) -> float:
        try:
            return float(self.cx.get("max_gb") or 10)
        except ValueError:
            return 10.0

    def _token(self) -> str:
        k = self._chave()
        agora = int(time.time())
        uri = k.get("token_uri") or "https://oauth2.googleapis.com/token"
        assertion = jwt_rs256(k["private_key"], {"iss": k["client_email"], "scope": "https://www.googleapis.com/auth/bigquery",
                                                 "aud": uri, "iat": agora, "exp": agora + 3600})
        _, r = _req(uri, data=urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST", explicar=self._explicar, onde="o Google")
        if not r.get("access_token"):
            raise Erro("O Google não devolveu token de acesso.")
        return r["access_token"]

    @staticmethod
    def _linhas(r: dict) -> list[list]:
        return [[c.get("v") if not isinstance(c.get("v"), (list, dict)) else json.dumps(c.get("v"), ensure_ascii=False) for c in row.get("f", [])]
                for row in r.get("rows") or []]

    def executar(self, sql: str, linhas: int) -> Resultado:
        h = {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}
        kw = {"headers": h, "explicar": self._explicar, "onde": "o BigQuery"}
        corpo = {"query": sql, "useLegacySql": False, "maxResults": linhas, "timeoutMs": 50000,
                 "maximumBytesBilled": str(int(self._max_gb() * 1024 ** 3)), "labels": {"origem": TAG}}
        if self.cx.get("local"):
            corpo["location"] = self.cx["local"]
        proj = urllib.parse.quote(self.cx["projeto"])
        _, r = _req(f"{self.api()}/projects/{proj}/queries", data=json.dumps(corpo).encode(), method="POST", **kw)
        inicio = time.time()
        while not r.get("jobComplete"):
            job = r.get("jobReference") or {}
            if time.time() - inicio > TIMEOUT_S:
                _req(f"{self.api()}/projects/{proj}/jobs/{job.get('jobId')}/cancel?location={job.get('location', '')}", data=b"", method="POST", **kw)
                raise Erro(f"A consulta passou de {TIMEOUT_S}s e foi cancelada. Reduza o volume.")
            time.sleep(3)
            q = urllib.parse.urlencode({"location": job.get("location", ""), "maxResults": linhas, "timeoutMs": 50000})
            _, r = _req(f"{self.api()}/projects/{proj}/queries/{job.get('jobId')}?{q}", **kw)
        cols = [f["name"] for f in (r.get("schema") or {}).get("fields", [])]
        dados = self._linhas(r)
        total = int(r.get("totalRows") or len(dados))
        extra = []
        if r.get("totalBytesProcessed"):
            extra.append(f"{int(r['totalBytesProcessed']) / 1024 ** 3:.2f} GB processados")
        return Resultado(cols, dados, total > len(dados), extra)

    def amostra(self, partes: list[str], n: int) -> Resultado:
        # tabledata.list não executa consulta: amostrar não custa nada
        h = {"Authorization": f"Bearer {self._token()}"}
        kw = {"headers": h, "explicar": self._explicar, "onde": "o BigQuery"}
        p, ds, t = (urllib.parse.quote(x) for x in partes)
        _, meta = _req(f"{self.api()}/projects/{p}/datasets/{ds}/tables/{t}", **kw)
        if meta.get("type") not in (None, "TABLE"):
            return self.executar(self.sql_amostra(partes, n), n)
        cols = [f["name"] for f in (meta.get("schema") or {}).get("fields", [])]
        _, r = _req(f"{self.api()}/projects/{p}/datasets/{ds}/tables/{t}/data?maxResults={n}", **kw)
        dados = self._linhas(r)
        return Resultado(cols, dados, int(r.get("totalRows") or 0) > len(dados), ["amostra sem custo (tabledata.list)"])

    def dbt_profile(self, schema_alvo: str, pasta: Path) -> dict:
        proj, ds = schema_alvo.split(".")
        arq = pasta / "gcp-sa.json"
        arq.write_text(json.dumps(self._chave()), encoding="utf-8")
        arq.chmod(0o600)
        p = {"type": "bigquery", "method": "service-account", "keyfile": str(arq), "project": proj, "dataset": ds,
             "threads": 4, "maximum_bytes_billed": int(self._max_gb() * 1024 ** 3), "labels": {"origem": TAG}}
        if self.cx.get("local"):
            p["location"] = self.cx["local"]
        return p


class Fabric(Plataforma):
    nome, rotulo = "fabric", "Microsoft Fabric"
    campos = {"servidor": "SQL connection string do workspace", "banco": "warehouse padrão (a sandbox)", "tenant_id": "ID do tenant Microsoft Entra"}
    segredos = ("FABRIC_CLIENT_ID", "FABRIC_CLIENT_SECRET")
    teste = "SELECT SUSER_SNAME() AS usuario, DB_NAME() AS banco"
    guia = "docs/acesso-dados/fabric.md"

    def q(self, partes: list[str]) -> str:
        return ".".join(f"[{p}]" for p in partes)

    def sql_amostra(self, partes: list[str], n: int) -> str:
        return f"SELECT TOP {n} * FROM {self.q(partes)}"

    def sql_bancos(self) -> str:
        return "SELECT name AS banco FROM sys.databases ORDER BY 1"

    def sql_tabelas(self, banco: str, schema: str | None) -> str:
        filtro = f" AND lower(TABLE_SCHEMA) = '{schema}'" if schema else ""
        return (f"SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM {self.q([banco])}.INFORMATION_SCHEMA.TABLES "
                f"WHERE TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'queryinsights'){filtro} ORDER BY 1, 2")

    def sql_colunas(self, banco: str, schema: str) -> str:
        return (f"SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM {self.q([banco])}.INFORMATION_SCHEMA.COLUMNS "
                f"WHERE lower(TABLE_SCHEMA) = '{schema}' ORDER BY TABLE_NAME, ORDINAL_POSITION")

    def servidor(self) -> str:
        s = re.sub(r"^\w+://", "", self.cx["servidor"].strip()).split("/")[0]
        return s.split(",")[0].split(":")[0]

    def _explicar(self, status: int, j: dict) -> str:
        msg = str(j.get("error_description") or j.get("error") or j)
        base = f"HTTP {status}: {msg.splitlines()[0]}"
        if status in (400, 401) and re.search(r"AADSTS7000215|invalid_client", msg):
            return f"Client secret inválido ou expirado (FABRIC_CLIENT_SECRET). [{base}]"
        if re.search(r"AADSTS700016|unauthorized_client", msg):
            return f"Aplicativo não encontrado no tenant: confira FABRIC_CLIENT_ID e dados.conexao.tenant_id. [{base}]"
        if re.search(r"AADSTS90002", msg):
            return f"Tenant não encontrado: confira dados.conexao.tenant_id. [{base}]"
        return base

    def token(self) -> str:
        base = os.environ.get("DADOS_URL_BASE") or "https://login.microsoftonline.com"
        _, r = _req(f"{base}/{urllib.parse.quote(self.cx['tenant_id'])}/oauth2/v2.0/token",
                    data=urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": _segredo("FABRIC_CLIENT_ID"),
                                                 "client_secret": _segredo("FABRIC_CLIENT_SECRET"),
                                                 "scope": "https://database.windows.net/.default"}).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
                    explicar=self._explicar, onde="o Microsoft Entra ID")
        if not r.get("access_token"):
            raise Erro("O Entra ID não devolveu token de acesso.")
        return r["access_token"]

    def executar(self, sql: str, linhas: int) -> Resultado:
        try:
            import pyodbc  # type: ignore
        except ImportError:
            raise Erro("Driver do Fabric ausente (pyodbc + ODBC Driver 18). No GitHub Actions ele é instalado "
                       "automaticamente quando dados.plataforma = fabric; na sua máquina: pip install pyodbc e instale o msodbcsql18.") from None
        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if not drivers:
            raise Erro("ODBC Driver 18 for SQL Server não está instalado.")
        tk = self.token().encode("utf-16-le")
        attrs = {1256: struct.pack(f"<I{len(tk)}s", len(tk), tk)}  # SQL_COPT_SS_ACCESS_TOKEN
        conn_str = (f"Driver={{{sorted(drivers)[-1]}}};Server=tcp:{self.servidor()},1433;Database={self.cx['banco']};"
                    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;APP=" + TAG)
        try:
            conn = pyodbc.connect(conn_str, attrs_before=attrs, autocommit=True, timeout=60)
        except pyodbc.Error as e:
            m = str(e)
            if re.search(r"Login failed|18456", m):
                raise Erro("O Fabric recusou o login do service principal: ele precisa de acesso ao workspace ou ao item "
                           f"e o admin precisa liberar 'Service principals can use Fabric APIs'. [{m[:300]}]") from None
            raise Erro(f"Não foi possível conectar ao Fabric: {m[:300]}") from None
        try:
            conn.timeout = TIMEOUT_S
            cur = conn.cursor()
            cur.execute(sql)
            if not cur.description:
                return Resultado([], [])
            cols = [d[0] for d in cur.description]
            dados = [list(r) for r in cur.fetchmany(linhas + 1)]
            return Resultado(cols, dados[:linhas], len(dados) > linhas)
        except pyodbc.Error as e:
            raise Erro(f"Erro no Fabric: {str(e)[:400]}") from None
        finally:
            conn.close()

    def dbt_profile(self, schema_alvo: str, pasta: Path) -> dict:
        banco, sch = schema_alvo.split(".")
        return {"type": "fabric", "driver": "ODBC Driver 18 for SQL Server", "server": self.servidor(), "port": 1433,
                "database": banco, "schema": sch, "authentication": "ServicePrincipal", "tenant_id": self.cx["tenant_id"],
                "client_id": "{{ env_var('FABRIC_CLIENT_ID') }}", "client_secret": "{{ env_var('FABRIC_CLIENT_SECRET') }}",
                "threads": 4}


PLATAFORMAS = {p.nome: p for p in (Databricks, Snowflake, BigQuery, Fabric)}


def plataforma(c: dict) -> Plataforma:
    if not c["plataforma"]:
        raise Erro(f"Acesso a dados não configurado nesta squad. O Operador configura em {CONSOLE} "
                   "(guia: docs/acesso-dados.md). Não peça credenciais em specs, PRs ou mensagens.")
    cls = PLATAFORMAS.get(c["plataforma"])
    if not cls:
        raise Erro(f"Plataforma '{c['plataforma']}' sem acesso a dados pelos agentes. Use: {', '.join(PLATAFORMAS)}.")
    p = cls(c)
    f = p.faltando()
    if f:
        raise Erro(f"Acesso ao {p.rotulo} não configurado nesta squad. Falta: " + "; ".join(f) + ". "
                   f"O Operador configura em {CONSOLE} (guia: {p.guia}). Não peça credenciais em specs, PRs ou mensagens.")
    return p


# ----------------------------------------------------------------- saída

def tabela_md(colunas: list[str], linhas: list[list]) -> str:
    def cel(v):
        s = "∅" if v is None else str(v)
        return s.replace("|", "\\|").replace("\n", " ")[:120]
    out = ["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas)]
    out += ["| " + " | ".join(cel(v) for v in l) + " |" for l in linhas]
    return "\n".join(out)


def imprimir(r: Resultado, linhas: int) -> None:
    if not r.colunas:
        print("OK (sem resultado tabular).")
        return
    dados, mascaradas = mascarar(r.colunas, r.linhas)
    print(tabela_md(r.colunas, dados))
    rodape = [f"{len(dados)} linha(s)"]
    if r.truncado:
        rodape.append(f"resultado limitado a {linhas}")
    rodape += r.extra
    if mascaradas:
        rodape.append("colunas mascaradas (possível dado pessoal): " + ", ".join(mascaradas))
    print("\n_" + " · ".join(rodape) + "_")


def rodar(p: Plataforma, sql: str, linhas: int) -> None:
    linhas = max(1, min(linhas, LIMITE_MAXIMO))
    validar_sql(sql, p.c["escrita"])
    imprimir(p.executar(sql, linhas), linhas)


RE_PARTE = re.compile(r"^[A-Za-z_][\w\-]*$")


def _partes(nome: str, n: int, exemplo: str) -> list[str]:
    partes = _limpar_nome(nome).split(".")
    if len(partes) != n or not all(RE_PARTE.match(x) for x in partes):
        raise Erro(f"Use o nome completo: {exemplo}")
    return partes


def gerar_dbt_profile(p: Plataforma, pasta: Path) -> Path:
    if not p.c["escrita"]:
        raise Erro("dbt precisa da sandbox (dados.escrita): é o schema de destino dos modelos.")
    pasta.mkdir(parents=True, exist_ok=True)
    perfil = {"squad": {"target": "sandbox", "outputs": {"sandbox": p.dbt_profile(p.c["escrita"], pasta)}}}
    arq = pasta / "profiles.yml"
    arq.write_text("# gerado por scripts/dados.py — não versionar\n" + json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    arq.chmod(0o600)
    return arq


# ----------------------------------------------------------------- comandos

def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    opcoes: dict[str, str] = {}
    for flag in ("--linhas", "--saida"):
        if flag in args:
            i = args.index(flag)
            opcoes[flag] = args[i + 1] if i + 1 < len(args) else ""
            args = args[:i] + args[i + 2:]
    linhas = int(opcoes.get("--linhas") or LIMITE_PADRAO)
    c = config()
    try:
        if cmd == "plataforma":  # usado pelo workflow
            print(c["plataforma"] if c["plataforma"] in PLATAFORMAS else "")
            return 0
        if cmd == "usa-dbt":
            print("sim" if c["dbt"] and c["plataforma"] in PLATAFORMAS else "nao")
            return 0
        if cmd == "status":
            cls = PLATAFORMAS.get(c["plataforma"])
            print(json.dumps({
                "plataforma": c["plataforma"] or None,
                "conexao": c["conexao"],
                "leitura": c["leitura"],
                "escrita": c["escrita"] or None,
                "dbt": c["dbt"],
                "credenciais": ("presentes" if cls and all(_segredo(s) for s in cls.segredos) else "ausentes"),
                "faltando": cls(c).faltando() if cls else ["dados.plataforma em .squad/squad.yaml"],
            }, ensure_ascii=False, indent=2))
            return 0
        p = plataforma(c)
        if cmd == "testar":
            rodar(p, p.teste, 1)
        elif cmd == "dbt-profile":
            if not opcoes.get("--saida"):
                raise Erro("Informe --saida <pasta> (fora do repositório).")
            pasta = Path(opcoes["--saida"]).expanduser().resolve()
            if pasta == ROOT or ROOT in pasta.parents:
                raise Erro("O profiles.yml não pode ficar dentro do repositório.")
            print(gerar_dbt_profile(p, pasta))
        elif cmd == "catalogo":
            alvo = _limpar_nome(args[0]) if args else ""
            if alvo:
                partes = alvo.split(".")
                if len(partes) > 2 or not all(RE_PARTE.match(x) for x in partes):
                    raise Erro("Use banco ou banco.schema.")
                sql = p.sql_tabelas(partes[0], None) if len(partes) == 1 else p.sql_colunas(partes[0], partes[1])
                rodar(p, sql, LIMITE_MAXIMO)
            elif not c["leitura"]:
                rodar(p, p.sql_bancos(), LIMITE_MAXIMO)
            else:
                for item in c["leitura"]:
                    print(f"\n### {item}\n")
                    partes = item.split(".")
                    try:
                        rodar(p, p.sql_tabelas(partes[0], partes[1] if len(partes) > 1 else None), LIMITE_MAXIMO)
                    except Erro as e:
                        print(f"ERRO em {item}: {e}")
        elif cmd == "amostra":
            if not args:
                raise Erro("Informe a tabela: banco.schema.tabela")
            n = max(1, min(linhas, LIMITE_MAXIMO))
            imprimir(p.amostra(_partes(args[0], 3, "banco.schema.tabela"), n), n)
        elif cmd == "sql":
            if not args:
                raise Erro('Informe a instrução: python scripts/dados.py sql "SELECT ..."')
            rodar(p, " ".join(args), linhas)
        else:
            raise Erro(f"Comando desconhecido: {cmd}. Veja: python scripts/dados.py ajuda")
    except Erro as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
