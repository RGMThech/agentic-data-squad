#!/usr/bin/env python3
"""Validador da squad de IA e ML.

- model cards (modelos/*/model-card.md): seções obrigatórias
- avaliações (avaliacoes/**/eval.yaml): campos, métricas com valor/limiar/direção e resultado coerente
- prompts e avaliações sem CPF, e-mail ou telefone
- abordagem (design.md) em revisão ou aprovada: seções obrigatórias
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import ROOT, carregar_yaml, faltando_secoes, ler_documento, procurar_pii, relatar

SECOES_CARD = ["Visão geral", "Uso pretendido", "Usos fora do escopo", "Dados", "Avaliação", "Limitações e riscos"]
SECOES_ABORDAGEM = ["Abordagem", "Plano de avaliação", "Riscos de IA responsável"]
TEXTO = {".md", ".txt", ".yaml", ".yml", ".json", ".jsonl", ".csv"}


def passou(m: dict) -> bool:
    v, lim = float(m["valor"]), float(m["limiar"])
    return v <= lim if str(m.get("direcao", "maior")) == "menor" else v >= lim


def checar_eval(arq: Path, raiz: Path) -> list[str]:
    rel = arq.relative_to(raiz)
    d = carregar_yaml(arq) or {}
    if not isinstance(d, dict):
        return [f"{rel}: formato inválido (use templates/eval.yaml)"]
    erros = [f"{rel}: campo obrigatório vazio: {c}" for c in ("modelo", "dataset", "metricas", "resultado") if not d.get(c)]
    metricas = d.get("metricas") or []
    reprovadas = []
    for m in metricas if isinstance(metricas, list) else []:
        try:
            if str(m.get("direcao", "maior")) not in ("maior", "menor"):
                erros.append(f"{rel}: métrica {m.get('nome')}: direcao deve ser maior ou menor")
            elif not passou(m):
                reprovadas.append(str(m.get("nome")))
        except (KeyError, TypeError, ValueError, AttributeError):
            erros.append(f"{rel}: métrica {m.get('nome') if isinstance(m, dict) else m}: precisa de nome, valor e limiar numéricos")
    resultado = str(d.get("resultado") or "")
    if resultado not in ("", "aprovado", "reprovado"):
        erros.append(f"{rel}: resultado deve ser aprovado ou reprovado")
    if resultado == "aprovado" and reprovadas:
        erros.append(f"{rel}: resultado 'aprovado', mas abaixo do limiar: {', '.join(reprovadas)}")
    return erros


def checar(raiz: Path = ROOT) -> list[str]:
    erros: list[str] = []
    for card in sorted((raiz / "modelos").glob("*/model-card.md")):
        _, corpo = ler_documento(card)
        erros += [f"{card.relative_to(raiz)}: falta a seção '{s}'" for s in faltando_secoes(corpo, SECOES_CARD)]
    for ev in sorted((raiz / "avaliacoes").rglob("eval.y*ml")):
        erros += checar_eval(ev, raiz)
    for pasta in ("prompts", "avaliacoes"):
        for arq in sorted((raiz / pasta).rglob("*")):
            if arq.is_file() and arq.suffix.lower() in TEXTO:
                achados = procurar_pii(arq.read_text(encoding="utf-8", errors="ignore"))
                if achados:
                    erros.append(f"{arq.relative_to(raiz)}: possível dado pessoal ({', '.join(achados)}). Use dados sintéticos ou anonimizados.")
    for design in sorted((raiz / "specs").glob("*/design.md")):
        meta, corpo = ler_documento(design)
        if meta.get("status") in ("em_revisao", "aprovado"):
            erros += [f"{design.relative_to(raiz)}: falta a seção '{s}'" for s in faltando_secoes(corpo, SECOES_ABORDAGEM)]
    return erros


if __name__ == "__main__":
    sys.exit(relatar("ia", checar()))
