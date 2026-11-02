"""Utilidades compartilhadas pelos validadores do harness."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CAMADAS = {"bronze": "brz", "silver": "slv", "gold": "gld"}
PREFIXO_PARA_CAMADA = {v: k for k, v in CAMADAS.items()}

RE_TABELA = re.compile(r"^(brz|slv|gld)_([a-z][a-z0-9]{1,19})__([a-z][a-z0-9]*(?:_[a-z0-9]+)*)$")
RE_DOMINIO = re.compile(r"^[a-z][a-z0-9]{1,19}$")
RE_COLUNA = re.compile(r"^_?[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
RE_SPEC_DIR = re.compile(r"^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")

EXTENSOES_PIPELINE = {".sql", ".py"}


def ler_frontmatter(caminho: Path) -> dict[str, str]:
    """Lê um front matter YAML simples (chave: valor) sem depender de PyYAML."""
    texto = caminho.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        return {}
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return {}
    dados: dict[str, str] = {}
    for linha in partes[1].splitlines():
        linha = linha.split("#", 1)[0].rstrip()
        if ":" in linha and not linha.startswith(" "):
            chave, valor = linha.split(":", 1)
            dados[chave.strip()] = valor.strip()
    return dados


def carregar_yaml(caminho: Path):
    try:
        import yaml  # type: ignore
    except ImportError:
        sys.exit("PyYAML não instalado. Rode: pip install pyyaml")
    with caminho.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def relatar(nome: str, erros: list[str]) -> int:
    if erros:
        print(f"❌ {nome}: {len(erros)} problema(s)", file=sys.stderr)
        for e in erros:
            print(f"   - {e}", file=sys.stderr)
        return 1
    print(f"✅ {nome}: ok")
    return 0


# --- Documentos com front matter e varredura de dados pessoais (usados pelos validadores dos tipos) ---

RE_PII = {
    "CPF": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "CPF sem pontuação": re.compile(r"(?<![\d.])\d{11}(?![\d.])"),
    "e-mail": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "telefone": re.compile(r"(?<!\d)\(?\d{2}\)?[\s-]?9\d{4}[\s-]?\d{4}(?!\d)"),
}

# e-mails genéricos que podem aparecer em exemplos e documentação
EMAILS_PERMITIDOS = re.compile(r"@(exemplo|example)\.(com|com\.br|org)$|^(nao-responda|noreply|no-reply)@", re.I)


def procurar_pii(texto: str, tipos: tuple[str, ...] = ("CPF", "e-mail", "telefone")) -> list[str]:
    """Lista os tipos de dado pessoal encontrados no texto (sem repetir o valor encontrado)."""
    achados = []
    for nome in tipos:
        for m in RE_PII[nome].finditer(texto):
            if nome == "e-mail" and EMAILS_PERMITIDOS.search(m.group(0)):
                continue
            achados.append(nome)
            break
    return achados


def ler_documento(caminho: Path) -> tuple[dict, str]:
    """(front matter YAML, corpo) de um markdown. Front matter inválido vira {}."""
    texto = caminho.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        return {}, texto
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return {}, texto
    try:
        import yaml  # type: ignore

        meta = yaml.safe_load(partes[1]) or {}
    except Exception:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), partes[2]


def secoes(texto: str) -> list[str]:
    """Títulos de seção (##) de um markdown, sem numeração."""
    return [re.sub(r"^\d+[.)]\s*", "", m.group(1)).strip() for m in re.finditer(r"^##\s+(.+)$", texto, re.M)]


def faltando_secoes(texto: str, obrigatorias: list[str]) -> list[str]:
    tem = [s.lower() for s in secoes(texto)]
    return [o for o in obrigatorias if not any(o.lower() in t for t in tem)]


RE_HISTORIA = re.compile(r"\bcomo\b.+?,\s*quero\b.+?,\s*para\b", re.I)
