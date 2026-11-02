#!/usr/bin/env python3
"""Validador da squad de produto.

- PRD (design.md) em revisão ou aprovado: seções obrigatórias e histórias "Como…, quero…, para…"
- backlog (backlog/*.yaml): campos dos itens e nota RICE consistente
- pesquisa (pesquisa/**): sem CPF, e-mail ou telefone de participantes
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import RE_HISTORIA, ROOT, carregar_yaml, faltando_secoes, ler_documento, procurar_pii, relatar

SECOES_PRD = ["Problema e contexto", "Objetivos e métricas", "Escopo", "Fora de escopo", "Histórias de usuário", "Requisitos", "Riscos e dependências", "Plano de lançamento"]
IMPACTOS = {0.25, 0.5, 1, 2, 3}
TEXTO = {".md", ".txt", ".csv", ".yaml", ".yml", ".json", ".html"}


def rice(r: dict) -> float:
    return float(r["alcance"]) * float(r["impacto"]) * float(r["confianca"]) / float(r["esforco"])


def checar_item(rel: str, item: dict) -> list[str]:
    iid = item.get("id", "?")
    erros = [f"{rel} {iid}: campo obrigatório vazio: {c}" for c in ("id", "titulo", "historia") if not item.get(c)]
    if item.get("historia") and not RE_HISTORIA.search(str(item["historia"])):
        erros.append(f"{rel} {iid}: história fora do formato 'Como…, quero…, para…'")
    r = item.get("rice")
    if not isinstance(r, dict):
        return erros + [f"{rel} {iid}: sem bloco rice"]
    try:
        if float(r["impacto"]) not in IMPACTOS:
            erros.append(f"{rel} {iid}: impacto {r['impacto']} fora da escala (0.25, 0.5, 1, 2, 3)")
        if not 0 <= float(r["confianca"]) <= 1:
            erros.append(f"{rel} {iid}: confiança deve ficar entre 0 e 1")
        if float(r["esforco"]) <= 0:
            erros.append(f"{rel} {iid}: esforço deve ser maior que zero")
        elif "rice_score" in item and abs(float(item["rice_score"]) - rice(r)) > max(0.5, 0.01 * rice(r)):
            erros.append(f"{rel} {iid}: rice_score {item['rice_score']} não bate com o cálculo ({rice(r):.1f})")
    except (KeyError, TypeError, ValueError) as e:
        erros.append(f"{rel} {iid}: rice incompleto ou inválido ({e})")
    return erros


def checar(raiz: Path = ROOT) -> list[str]:
    erros: list[str] = []
    for design in sorted((raiz / "specs").glob("*/design.md")):
        meta, corpo = ler_documento(design)
        if meta.get("status") in ("em_revisao", "aprovado"):
            rel = design.relative_to(raiz)
            erros += [f"{rel}: falta a seção '{s}'" for s in faltando_secoes(corpo, SECOES_PRD)]
            if not RE_HISTORIA.search(corpo):
                erros.append(f"{rel}: nenhuma história no formato 'Como…, quero…, para…'")
    for arq in sorted((raiz / "backlog").glob("*.y*ml")):
        rel = str(arq.relative_to(raiz))
        dados = carregar_yaml(arq) or {}
        itens = dados.get("itens") if isinstance(dados, dict) else None
        if not isinstance(itens, list):
            erros.append(f"{rel}: esperado uma lista em 'itens'")
            continue
        for item in itens:
            erros += checar_item(rel, item if isinstance(item, dict) else {})
    for arq in sorted((raiz / "pesquisa").rglob("*")):
        if arq.is_file() and arq.suffix.lower() in TEXTO:
            achados = procurar_pii(arq.read_text(encoding="utf-8", errors="ignore"))
            if achados:
                erros.append(f"{arq.relative_to(raiz)}: possível dado pessoal ({', '.join(achados)}). Anonimize os participantes (P1, P2…).")
    return erros


if __name__ == "__main__":
    sys.exit(relatar("produto", checar()))
