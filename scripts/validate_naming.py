#!/usr/bin/env python3
"""Valida a convenção de nomes dos pipelines, contratos e specs.

Uso:
    python scripts/validate_naming.py              # valida o repositório inteiro
    python scripts/validate_naming.py <arquivos>   # valida só os arquivos informados
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import (
    CAMADAS,
    EXTENSOES_PIPELINE,
    PREFIXO_PARA_CAMADA,
    RE_DOMINIO,
    RE_SPEC_DIR,
    RE_TABELA,
    ROOT,
    relatar,
)


def validar_pipeline(caminho: Path) -> list[str]:
    rel = caminho.relative_to(ROOT)
    partes = rel.parts  # pipelines/<camada>/<dominio>/<arquivo>
    if caminho.name.startswith(("__init__", ".")) or caminho.suffix not in EXTENSOES_PIPELINE:
        return []
    if len(partes) != 4:
        return [f"{rel}: deve estar em pipelines/<camada>/<dominio>/<arquivo>"]
    _, camada, dominio, _ = partes
    erros: list[str] = []
    if camada not in CAMADAS:
        erros.append(f"{rel}: camada '{camada}' inválida (use {', '.join(CAMADAS)})")
        return erros
    if not RE_DOMINIO.match(dominio):
        erros.append(f"{rel}: domínio '{dominio}' inválido (minúsculo, sem acento, 2–20 chars)")
    m = RE_TABELA.match(caminho.stem)
    if not m:
        erros.append(f"{rel}: nome deve seguir <camada>_<dominio>__<entidade> (ex.: slv_vendas__pedidos)")
        return erros
    prefixo, dom_nome, _ = m.groups()
    if PREFIXO_PARA_CAMADA[prefixo] != camada:
        erros.append(f"{rel}: prefixo '{prefixo}' não corresponde à pasta '{camada}' (esperado '{CAMADAS[camada]}')")
    if dom_nome != dominio:
        erros.append(f"{rel}: domínio no nome ('{dom_nome}') difere da pasta ('{dominio}')")
    return erros


def validar_contrato_nome(caminho: Path) -> list[str]:
    if caminho.suffix not in {".yaml", ".yml"}:
        return []
    if not RE_TABELA.match(caminho.stem):
        return [f"{caminho.relative_to(ROOT)}: nome do contrato deve ser o nome da tabela"]
    return []


def validar_spec_dir(caminho: Path) -> list[str]:
    if not RE_SPEC_DIR.match(caminho.name):
        return [f"specs/{caminho.name}: pasta deve seguir NNN-slug (ex.: 001-receita-diaria)"]
    return []


def coletar(arquivos: list[Path] | None) -> list[str]:
    erros: list[str] = []
    if arquivos:
        for a in arquivos:
            a = a.resolve()
            try:
                rel = a.relative_to(ROOT)
            except ValueError:
                continue
            if rel.parts[:1] == ("pipelines",) and a.is_file():
                erros += validar_pipeline(a)
            elif rel.parts[:1] == ("contracts",) and a.is_file():
                erros += validar_contrato_nome(a)
            elif rel.parts[:1] == ("specs",) and len(rel.parts) >= 2:
                erros += validar_spec_dir(ROOT / "specs" / rel.parts[1])
        return erros

    for p in sorted((ROOT / "pipelines").rglob("*")):
        if p.is_file():
            erros += validar_pipeline(p)
    for p in sorted((ROOT / "contracts").glob("*")):
        if p.is_file():
            erros += validar_contrato_nome(p)
    for p in sorted((ROOT / "specs").iterdir()):
        if p.is_dir():
            erros += validar_spec_dir(p)
    return erros


def main(argv: list[str]) -> int:
    arquivos = [Path(a) for a in argv] or None
    return relatar("naming", coletar(arquivos))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
