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
