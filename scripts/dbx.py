#!/usr/bin/env python3
"""Acesso dos agentes ao Databricks (SQL warehouse), com travas de segurança.

A segurança de verdade é do Unity Catalog: o service principal da squad só tem
leitura nas fontes e escrita no schema de sandbox. Este script acrescenta travas:
  - uma instrução por vez; GRANT/REVOKE e afins sempre bloqueados
  - escrita (CREATE/INSERT/MERGE/…) só em objetos do schema de escrita
  - limite de linhas devolvidas
  - colunas com cara de dado pessoal mascaradas na saída

Uso:
  python scripts/dbx.py status                      # mostra a configuração (sem segredos)
  python scripts/dbx.py testar                      # autentica e roda SELECT current_user()
  python scripts/dbx.py catalogo [catalogo.schema]  # lista schemas, tabelas e colunas visíveis
  python scripts/dbx.py amostra <catalogo.schema.tabela> [--linhas 20]
  python scripts/dbx.py sql "<instrução>" [--linhas 50]

Configuração:
  .squad/squad.yaml → bloco "databricks" (host, warehouse_id, leitura, escrita)
  segredos (GitHub Actions): DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET
  Variáveis DATABRICKS_HOST / DATABRICKS_WAREHOUSE_ID / DATABRICKS_LEITURA /
  DATABRICKS_ESCRITA sobrepõem o squad.yaml.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200
TIMEOUT_S = 300

RE_PII = re.compile(
    r"(cpf|cnpj|rg|email|e_mail|telefone|celular|fone|whats|nome|name|endereco|logradouro|cep|"
    r"nascimento|birth|senha|password|token|cartao|card|conta|iban|pis|cns|passaporte|ip_?addr)",
    re.I,
)
LEITURA = ("SELECT", "WITH", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "VALUES")
ESCRITA = ("CREATE", "INSERT", "MERGE", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "REPLACE", "COPY", "OPTIMIZE", "VACUUM", "COMMENT")
PROIBIDOS = ("GRANT", "REVOKE", "DENY", "SET OWNER", "USE CATALOG", "CREATE CATALOG", "DROP CATALOG", "CREATE CONNECTION",
             "CREATE EXTERNAL", "CREATE STORAGE CREDENTIAL", "CREATE SHARE", "CREATE RECIPIENT", "MSCK", "REFRESH FOREIGN")


class Erro(Exception):
    pass


# ----------------------------------------------------------------- configuração

def _yaml() -> dict:
    caminho = ROOT / ".squad" / "squad.yaml"
    if not caminho.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    return (yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}).get("databricks") or {}


def _lista(v) -> list[str]:
    if isinstance(v, str):
        v = v.split(",")
    return [str(x).strip().strip("`").lower() for x in (v or []) if str(x).strip()]


def config() -> dict:
    y = _yaml()
    host = (os.environ.get("DATABRICKS_HOST") or y.get("host") or "").strip().rstrip("/")
    if host and not host.startswith("http"):
        host = "https://" + host
    return {
        "host": host,
        "warehouse_id": (os.environ.get("DATABRICKS_WAREHOUSE_ID") or str(y.get("warehouse_id") or "")).strip(),
        "leitura": _lista(os.environ.get("DATABRICKS_LEITURA") or y.get("leitura")),
        "escrita": (os.environ.get("DATABRICKS_ESCRITA") or str(y.get("escrita") or "")).strip().strip("`").lower(),
        "client_id": os.environ.get("DATABRICKS_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("DATABRICKS_CLIENT_SECRET", "").strip(),
    }


def faltando(c: dict) -> list[str]:
    nomes = {
        "host": "databricks.host em .squad/squad.yaml",
        "warehouse_id": "databricks.warehouse_id em .squad/squad.yaml",
        "client_id": "segredo DATABRICKS_CLIENT_ID",
        "client_secret": "segredo DATABRICKS_CLIENT_SECRET",
    }
    return [nomes[k] for k in nomes if not c[k]]


# ----------------------------------------------------------------- travas

def _sem_comentarios_e_literais(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"'(?:[^'\\]|\\.|'')*'", "''", sql)
    sql = re.sub(r'"(?:[^"\\]|\\.)*"', '""', sql)
    return sql


def _alvos_de_escrita(sql: str) -> list[str]:
    """Objetos que a instrução cria/altera (nomes como aparecem, sem crases)."""
    padroes = [
        r"\b(?:CREATE|REPLACE)\s+(?:OR\s+REPLACE\s+)?(?:TEMPORARY\s+|TEMP\s+)?(?:MATERIALIZED\s+)?(?:TABLE|VIEW|SCHEMA|DATABASE|FUNCTION|VOLUME)\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\w.]+)",
        r"\bINSERT\s+(?:INTO|OVERWRITE)\s+(?:TABLE\s+)?([`\w.]+)",
        r"\bMERGE\s+INTO\s+([`\w.]+)",
        r"^\s*UPDATE\s+([`\w.]+)",
        r"\bDELETE\s+FROM\s+([`\w.]+)",
        r"\bDROP\s+(?:TABLE|VIEW|SCHEMA|DATABASE|FUNCTION|VOLUME|MATERIALIZED\s+VIEW)\s+(?:IF\s+EXISTS\s+)?([`\w.]+)",
        r"\bALTER\s+(?:TABLE|VIEW|SCHEMA|DATABASE)\s+([`\w.]+)",
        r"\bTRUNCATE\s+TABLE\s+([`\w.]+)",
        r"\bCOPY\s+INTO\s+([`\w.]+)",
        r"\b(?:OPTIMIZE|VACUUM)\s+([`\w.]+)",
        r"\bCOMMENT\s+ON\s+(?:TABLE|COLUMN|SCHEMA|VIEW)\s+([`\w.]+)",
    ]
    alvos: list[str] = []
    for p in padroes:
        alvos += [m.group(1).replace("`", "").lower() for m in re.finditer(p, sql, re.I)]
    return alvos


def validar_sql(sql: str, escrita: str) -> str:
    """Devolve 'leitura' ou 'escrita'; levanta Erro se a instrução não for permitida."""
    limpo = _sem_comentarios_e_literais(sql).strip().rstrip(";").strip()
    if not limpo:
        raise Erro("Instrução vazia.")
    if ";" in limpo:
        raise Erro("Envie uma instrução por vez (sem ';' no meio).")
    upper = re.sub(r"\s+", " ", limpo.upper())
    for p in PROIBIDOS:
        if re.search(rf"\b{p}\b", upper):
            raise Erro(f"'{p}' não é permitido aos agentes. Permissões são administradas pelo Operador no Databricks.")
    primeira = upper.split(" ", 1)[0]
    if primeira in LEITURA and not any(re.search(rf"\b{k}\b", upper) for k in ("INSERT", "MERGE", "DELETE", "UPDATE", "DROP", "ALTER", "TRUNCATE", "CREATE")):
        return "leitura"
    if primeira in ESCRITA or primeira in LEITURA:
        if not escrita:
            raise Erro("Escrita bloqueada: não há schema de escrita configurado (databricks.escrita em .squad/squad.yaml).")
        alvos = _alvos_de_escrita(limpo)
        if not alvos:
            raise Erro("Não consegui identificar o objeto alterado. Use nomes completos: catalogo.schema.tabela.")
        for a in alvos:
            partes = a.split(".")
            if len(partes) < 3 and not (len(partes) == 2 and a == escrita):
                raise Erro(f"Use o nome completo catalogo.schema.objeto para escrever (recebi '{a}').")
            schema = ".".join(partes[:2])
            if schema != escrita:
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


# ----------------------------------------------------------------- API

def _req(url: str, *, data: bytes | None = None, headers: dict | None = None, method: str | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = r.read().decode("utf-8") or "{}"
            return json.loads(corpo)
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")
        try:
            j = json.loads(corpo)
            msg = j.get("message") or j.get("error_description") or j.get("error") or corpo
            code = j.get("error_code") or j.get("error") or ""
        except json.JSONDecodeError:
            msg, code = corpo[:300], ""
        raise Erro(explicar(e.code, str(code), str(msg))) from None
    except urllib.error.URLError as e:
        raise Erro(f"Não foi possível conectar ao Databricks ({e.reason}). Confira databricks.host.") from None


def explicar(status: int, code: str, msg: str) -> str:
    base = f"HTTP {status} {code}: {msg}".strip()
    if status == 401 or "invalid_client" in code:
        return f"Credenciais recusadas: confira DATABRICKS_CLIENT_ID e DATABRICKS_CLIENT_SECRET (o secret expira). [{base}]"
    if status == 403 and "warehouse" in msg.lower():
        return f"O service principal não tem 'Can use' no SQL warehouse. [{base}]"
    if status == 403:
        return f"Permissão negada no Databricks. [{base}]"
    if status == 404 and "warehouse" in msg.lower():
        return f"SQL warehouse não encontrado: confira databricks.warehouse_id. [{base}]"
    return base


def token(c: dict) -> str:
    basic = base64.b64encode(f"{c['client_id']}:{c['client_secret']}".encode()).decode()
    r = _req(
        f"{c['host']}/oidc/v1/token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"}).encode(),
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    if not r.get("access_token"):
        raise Erro("O Databricks não devolveu token de acesso.")
    return r["access_token"]


def executar(c: dict, sql: str, linhas: int) -> dict:
    tk = token(c)
    h = {"Authorization": f"Bearer {tk}", "Content-Type": "application/json"}
    corpo = {
        "warehouse_id": c["warehouse_id"],
        "statement": sql,
        "wait_timeout": "50s",
        "on_wait_timeout": "CONTINUE",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
        "row_limit": linhas,
        "query_tags": [{"key": "origem", "value": "squad-agentica"}],
    }
    r = _req(f"{c['host']}/api/2.0/sql/statements/", data=json.dumps(corpo).encode(), headers=h, method="POST")
    inicio = time.time()
    while (r.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() - inicio > TIMEOUT_S:
            _req(f"{c['host']}/api/2.0/sql/statements/{r['statement_id']}/cancel", data=b"", headers=h, method="POST")
            raise Erro(f"A consulta passou de {TIMEOUT_S}s e foi cancelada. Reduza o volume (filtros, LIMIT).")
        time.sleep(3)
        r = _req(f"{c['host']}/api/2.0/sql/statements/{r['statement_id']}", headers=h)
    estado = (r.get("status") or {}).get("state")
    if estado != "SUCCEEDED":
        err = (r.get("status") or {}).get("error") or {}
        raise Erro(f"A consulta terminou como {estado}: {err.get('error_code', '')} {err.get('message', '')}".strip())
    return r


def tabela_md(colunas: list[str], linhas: list[list]) -> str:
    def cel(v):
        s = "∅" if v is None else str(v)
        return s.replace("|", "\\|").replace("\n", " ")[:120]
    out = ["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas)]
    out += ["| " + " | ".join(cel(v) for v in l) + " |" for l in linhas]
    return "\n".join(out)


def rodar(c: dict, sql: str, linhas: int) -> None:
    linhas = max(1, min(linhas, LIMITE_MAXIMO))
    validar_sql(sql, c["escrita"])
    r = executar(c, sql, linhas)
    cols = [x["name"] for x in ((r.get("manifest") or {}).get("schema") or {}).get("columns", [])]
    dados = (r.get("result") or {}).get("data_array") or []
    if not cols:
        print("OK (sem resultado tabular).")
        return
    dados, mascaradas = mascarar(cols, dados)
    print(tabela_md(cols, dados))
    total = (r.get("manifest") or {}).get("total_row_count")
    rodape = [f"{len(dados)} linha(s)"]
    if (r.get("manifest") or {}).get("truncated") or (total and total > len(dados)):
        rodape.append(f"resultado limitado a {linhas}")
    if mascaradas:
        rodape.append("colunas mascaradas (possível dado pessoal): " + ", ".join(mascaradas))
    print("\n_" + " · ".join(rodape) + "_")


# ----------------------------------------------------------------- comandos

def _exigir(c: dict) -> None:
    f = faltando(c)
    if f:
        raise Erro(
            "Acesso ao Databricks não configurado nesta squad. Falta: " + "; ".join(f) + ". "
            "O Operador configura em Squad Console → Configuração → Databricks (guia: docs/databricks.md). "
            "Não peça credenciais em specs, PRs ou mensagens."
        )


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    linhas = LIMITE_PADRAO
    if "--linhas" in args:
        i = args.index("--linhas")
        linhas = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    c = config()
    try:
        if cmd == "status":
            print(json.dumps({
                "host": c["host"] or None,
                "warehouse_id": c["warehouse_id"] or None,
                "leitura": c["leitura"],
                "escrita": c["escrita"] or None,
                "credenciais": "presentes" if c["client_id"] and c["client_secret"] else "ausentes",
                "faltando": faltando(c),
            }, ensure_ascii=False, indent=2))
            return 0
        _exigir(c)
        if cmd == "testar":
            rodar(c, "SELECT current_user() AS usuario, current_catalog() AS catalogo_padrao", 1)
        elif cmd == "catalogo":
            alvo = (args[0] if args else "").strip("`").lower()
            if alvo:
                partes = alvo.split(".")
                if len(partes) == 1:
                    sql = f"SELECT table_schema, table_name, table_type, comment FROM `{partes[0]}`.information_schema.tables WHERE table_schema <> 'information_schema' ORDER BY 1, 2"
                else:
                    sql = (f"SELECT table_name, column_name, data_type, comment FROM `{partes[0]}`.information_schema.columns "
                           f"WHERE table_schema = '{partes[1]}' ORDER BY table_name, ordinal_position")
                rodar(c, sql, LIMITE_MAXIMO)
            else:
                cats = c["leitura"] or []
                if not cats:
                    rodar(c, "SHOW CATALOGS", LIMITE_MAXIMO)
                for cat in cats:
                    print(f"\n### {cat}\n")
                    p = cat.split(".")
                    filtro = f" AND table_schema = '{p[1]}'" if len(p) > 1 else ""
                    rodar(c, f"SELECT table_schema, table_name, table_type, comment FROM `{p[0]}`.information_schema.tables WHERE table_schema <> 'information_schema'{filtro} ORDER BY 1, 2", LIMITE_MAXIMO)
        elif cmd == "amostra":
            if not args:
                raise Erro("Informe a tabela: catalogo.schema.tabela")
            nome = args[0].strip("`")
            if not re.fullmatch(r"[\w]+\.[\w]+\.[\w]+", nome):
                raise Erro("Use o nome completo: catalogo.schema.tabela")
            ident = ".".join(f"`{p}`" for p in nome.split("."))
            rodar(c, f"SELECT * FROM {ident} LIMIT {max(1, min(linhas, LIMITE_MAXIMO))}", min(linhas, LIMITE_MAXIMO))
        elif cmd == "sql":
            if not args:
                raise Erro('Informe a instrução: python scripts/dbx.py sql "SELECT ..."')
            rodar(c, " ".join(args), linhas)
        else:
            raise Erro(f"Comando desconhecido: {cmd}. Veja: python scripts/dbx.py ajuda")
    except Erro as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
