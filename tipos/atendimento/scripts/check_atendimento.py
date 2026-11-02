#!/usr/bin/env python3
"""Validador da squad de atendimento.

- artigos (kb/**/*.md) e macros (macros/*.md): front matter obrigatório; revisado_em em AAAA-MM-DD
- fluxos (fluxos/*.yaml): início, referências, alcance, saída para humano, sem beco sem saída, textos até 640
- kb, macros, fluxos e análises sem CPF, e-mail ou telefone
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from _common import ROOT, carregar_yaml, ler_documento, procurar_pii, relatar

CAMPOS_KB = ("titulo", "categoria", "publico", "status", "revisado_em")
CAMPOS_MACRO = ("titulo", "motivo", "status")
STATUS = {"rascunho", "em_revisao", "aprovado"}
TIPOS = {"mensagem", "pergunta", "acao", "humano", "fim"}
LIMITE_TEXTO = 640


def checar_doc(arq: Path, raiz: Path, campos: tuple[str, ...]) -> list[str]:
    rel = arq.relative_to(raiz)
    meta, _ = ler_documento(arq)
    if not meta:
        return [f"{rel}: sem front matter"]
    erros = [f"{rel}: campo obrigatório vazio: {c}" for c in campos if meta.get(c) in (None, "")]
    if meta.get("status") and meta["status"] not in STATUS:
        erros.append(f"{rel}: status '{meta['status']}' inválido ({' | '.join(sorted(STATUS))})")
    if "publico" in campos and meta.get("publico") and meta["publico"] not in ("cliente", "interno"):
        erros.append(f"{rel}: publico deve ser cliente ou interno")
    r = meta.get("revisado_em")
    if r not in (None, "") and not isinstance(r, date):
        try:
            date.fromisoformat(str(r))
        except ValueError:
            erros.append(f"{rel}: revisado_em '{r}' não está no formato AAAA-MM-DD")
    return erros


def saidas(no: dict) -> list[str]:
    out = [no["proximo"]] if no.get("proximo") else []
    for op in no.get("opcoes") or []:
        if isinstance(op, dict) and op.get("proximo"):
            out.append(op["proximo"])
    return [str(x) for x in out]


def checar_fluxo(arq: Path, raiz: Path) -> list[str]:
    rel = arq.relative_to(raiz)
    f = carregar_yaml(arq) or {}
    nos = f.get("nos") if isinstance(f, dict) else None
    if not isinstance(nos, dict) or not nos:
        return [f"{rel}: fluxo sem 'nos' (use templates/fluxo.yaml)"]
    erros = []
    inicio = str(f.get("inicio") or "")
    if inicio not in nos:
        erros.append(f"{rel}: 'inicio' ({inicio or 'vazio'}) não é um nó do fluxo")
    for nid, no in nos.items():
        if not isinstance(no, dict):
            erros.append(f"{rel}: nó '{nid}' inválido")
            continue
        tipo = no.get("tipo")
        if tipo not in TIPOS:
            erros.append(f"{rel}: nó '{nid}' com tipo '{tipo}' ({' | '.join(sorted(TIPOS))})")
        if len(str(no.get("texto") or "")) > LIMITE_TEXTO:
            erros.append(f"{rel}: nó '{nid}' com texto acima de {LIMITE_TEXTO} caracteres")
        for destino in saidas(no):
            if destino not in nos:
                erros.append(f"{rel}: nó '{nid}' aponta para '{destino}', que não existe")
        if tipo in ("mensagem", "pergunta", "acao") and not saidas(no):
            erros.append(f"{rel}: nó '{nid}' não leva a lugar nenhum (beco sem saída)")
        if tipo == "pergunta" and not no.get("opcoes"):
            erros.append(f"{rel}: pergunta '{nid}' sem opções")
    if inicio in nos:
        vistos, fila = set(), [inicio]
        while fila:
            atual = fila.pop()
            if atual in vistos or atual not in nos or not isinstance(nos[atual], dict):
                continue
            vistos.add(atual)
            fila += saidas(nos[atual])
        soltos = [n for n in nos if n not in vistos]
        if soltos:
            erros.append(f"{rel}: nós inalcançáveis a partir do início: {', '.join(soltos)}")
        if not any(isinstance(nos[n], dict) and nos[n].get("tipo") == "humano" for n in vistos):
            erros.append(f"{rel}: nenhum caminho leva a um atendente humano (nó tipo 'humano')")
    return erros


def checar(raiz: Path = ROOT) -> list[str]:
    erros: list[str] = []
    for arq in sorted((raiz / "kb").rglob("*.md")):
        if arq.name.lower() != "readme.md":
            erros += checar_doc(arq, raiz, CAMPOS_KB)
    for arq in sorted((raiz / "macros").rglob("*.md")):
        if arq.name.lower() != "readme.md":
            erros += checar_doc(arq, raiz, CAMPOS_MACRO)
    for arq in sorted((raiz / "fluxos").rglob("*.y*ml")):
        erros += checar_fluxo(arq, raiz)
    for pasta in ("kb", "macros", "fluxos", "analises"):
        for arq in sorted((raiz / pasta).rglob("*")):
            if arq.is_file() and arq.suffix.lower() in (".md", ".txt", ".yaml", ".yml", ".csv", ".json"):
                achados = procurar_pii(arq.read_text(encoding="utf-8", errors="ignore"))
                if achados:
                    erros.append(f"{arq.relative_to(raiz)}: possível dado de cliente ({', '.join(achados)}). Use exemplos fictícios.")
    return erros


if __name__ == "__main__":
    sys.exit(relatar("atendimento", checar()))
