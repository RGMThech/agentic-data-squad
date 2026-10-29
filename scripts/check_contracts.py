#!/usr/bin/env python3
"""Valida os data contracts e garante que todo pipeline silver/gold tem contrato.

Regras:
- campos obrigatórios presentes
- nome da tabela = nome do arquivo; camada/domínio coerentes com o nome
- colunas em snake_case, com classificação LGPD válida
- colunas 'pessoal' ou 'sensivel' exigem pii: true
- chave declarada existe nas colunas
- todo pipelines/silver|gold/** possui contracts/<tabela>.yaml
"""
from __future__ import annotations

import re
import sys

from _common import PREFIXO_PARA_CAMADA, RE_COLUNA, RE_TABELA, ROOT, carregar_yaml, relatar

OBRIGATORIOS = ["tabela", "versao", "camada", "dominio", "descricao", "owner", "grao", "chave", "colunas", "sla"]
CLASSIFICACOES = {"publico", "pessoal", "sensivel", "anonimizado"}
RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def validar_contrato(caminho) -> list[str]:
    rel = caminho.relative_to(ROOT)
    dados = carregar_yaml(caminho) or {}
    erros: list[str] = []

    for campo in OBRIGATORIOS:
        if campo not in dados or dados[campo] in (None, "", []):
            erros.append(f"{rel}: campo obrigatório ausente: '{campo}'")
    if erros:
        return erros

    tabela = dados["tabela"]
    if tabela != caminho.stem:
        erros.append(f"{rel}: 'tabela' ({tabela}) difere do nome do arquivo")
    m = RE_TABELA.match(tabela)
    if not m:
        erros.append(f"{rel}: nome de tabela inválido '{tabela}'")
    else:
        prefixo, dominio, _ = m.groups()
        if PREFIXO_PARA_CAMADA[prefixo] != dados["camada"]:
            erros.append(f"{rel}: camada '{dados['camada']}' não bate com prefixo '{prefixo}'")
        if dominio != dados["dominio"]:
            erros.append(f"{rel}: domínio '{dados['dominio']}' não bate com o nome da tabela")

    if not RE_SEMVER.match(str(dados["versao"])):
        erros.append(f"{rel}: versao deve ser semver (ex.: 1.0.0)")

    nomes = set()
    for i, col in enumerate(dados["colunas"]):
        nome = col.get("nome", f"<coluna {i}>")
        nomes.add(nome)
        if not RE_COLUNA.match(str(nome)):
            erros.append(f"{rel}: coluna '{nome}' fora do padrão snake_case")
        for campo in ("tipo", "descricao", "classificacao"):
            if not col.get(campo):
                erros.append(f"{rel}: coluna '{nome}' sem '{campo}'")
        classe = col.get("classificacao")
        if classe and classe not in CLASSIFICACOES:
            erros.append(f"{rel}: coluna '{nome}' com classificacao inválida '{classe}'")
        if classe in {"pessoal", "sensivel"} and col.get("pii") is not True:
            erros.append(f"{rel}: coluna '{nome}' é '{classe}' e precisa de pii: true")
        if col.get("descricao") and str(col["descricao"]).strip().lower() == str(nome).replace("_", " "):
            erros.append(f"{rel}: descrição da coluna '{nome}' apenas repete o nome")

    for k in dados["chave"]:
        if k not in nomes:
            erros.append(f"{rel}: chave '{k}' não existe em colunas")

    return erros


def main() -> int:
    erros: list[str] = []
    contratos = {p.stem: p for p in (ROOT / "contracts").glob("*.y*ml")}
    for p in sorted(contratos.values()):
        erros += validar_contrato(p)

    for camada in ("silver", "gold"):
        for p in sorted((ROOT / "pipelines" / camada).rglob("*")):
            if p.is_file() and p.suffix in {".sql", ".py"} and RE_TABELA.match(p.stem):
                if p.stem not in contratos:
                    erros.append(f"{p.relative_to(ROOT)}: sem contrato em contracts/{p.stem}.yaml")

    return relatar("contracts", erros)


if __name__ == "__main__":
    sys.exit(main())
