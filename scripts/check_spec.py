#!/usr/bin/env python3
"""Garante que nenhuma feature avance sem os gates G1/G2.

Regras:
- spec.md e design.md têm front matter com 'status' válido
- spec 'aprovado' não pode ter dúvidas abertas ("- [ ]" na seção Dúvidas abertas)
  e precisa de aprovado_por/aprovado_em
- design.md só pode existir como 'aprovado' se a spec estiver aprovada
- tasks.md só pode existir se spec e design estiverem aprovados
"""
from __future__ import annotations

import re
import sys

from _common import ROOT, ler_frontmatter, relatar

STATUS = {"rascunho", "em_revisao", "aprovado"}
SECOES_SPEC = ["Regras de negócio", "Métricas", "Critérios de aceite", "Dúvidas abertas"]


def duvidas_abertas(texto: str) -> list[str]:
    m = re.search(r"^## *\d*\.? *Dúvidas abertas\s*$(.*?)(?=^## |\Z)", texto, re.M | re.S)
    if not m:
        return []
    return [l.strip() for l in m.group(1).splitlines() if l.strip().startswith("- [ ]")]


def checar_aprovacao(rel, fm) -> list[str]:
    erros = []
    if fm.get("status") != "aprovado":
        return erros
    if not fm.get("aprovado_por") or not fm.get("aprovado_em"):
        erros.append(f"{rel}: status aprovado exige aprovado_por e aprovado_em (G = Operador)")
        return erros
    ops = operadores()
    if ops and fm.get("exemplo") != "true" and fm["aprovado_por"].lstrip("@") not in ops:
        erros.append(f"{rel}: aprovado_por '{fm['aprovado_por']}' não é operador em .squad/members.yaml")
    return erros


def operadores() -> set[str]:
    """Operadores declarados em .squad/members.yaml (vazio = sem checagem de papel)."""
    caminho = ROOT / ".squad" / "members.yaml"
    if not caminho.exists():
        return set()
    try:
        import yaml
    except ImportError:
        return set()
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return {str(o) for o in (dados.get("operadores") or [])}


def main() -> int:
    erros: list[str] = []
    for pasta in sorted(p for p in (ROOT / "specs").iterdir() if p.is_dir()):
        spec, design, tasks = pasta / "spec.md", pasta / "design.md", pasta / "tasks.md"
        if not spec.exists():
            erros.append(f"{pasta.relative_to(ROOT)}: sem spec.md")
            continue

        texto = spec.read_text(encoding="utf-8")
        fm = ler_frontmatter(spec)
        rel = spec.relative_to(ROOT)
        status_spec = fm.get("status")
        if status_spec not in STATUS:
            erros.append(f"{rel}: status inválido '{status_spec}'")
        for secao in SECOES_SPEC:
            if not re.search(rf"^## .*{re.escape(secao)}", texto, re.M):
                erros.append(f"{rel}: seção obrigatória ausente: '{secao}'")
        erros += checar_aprovacao(rel, fm)
        abertas = duvidas_abertas(texto)
        if status_spec == "aprovado" and abertas:
            erros.append(f"{rel}: aprovada com {len(abertas)} dúvida(s) aberta(s)")

        status_design = None
        if design.exists():
            fmd = ler_frontmatter(design)
            reld = design.relative_to(ROOT)
            status_design = fmd.get("status")
            if status_design not in STATUS:
                erros.append(f"{reld}: status inválido '{status_design}'")
            if status_spec != "aprovado":
                erros.append(f"{reld}: design iniciado sem spec aprovada (G1)")
            erros += checar_aprovacao(reld, fmd)

        if tasks.exists() and not (status_spec == "aprovado" and status_design == "aprovado"):
            erros.append(f"{tasks.relative_to(ROOT)}: tarefas criadas sem G1 e G2 aprovados")

    return relatar("specs/gates", erros)


if __name__ == "__main__":
    sys.exit(main())
