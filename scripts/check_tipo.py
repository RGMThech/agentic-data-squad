#!/usr/bin/env python3
"""Confere se a squad está coerente com o seu tipo (.squad/tipo.yaml).

- tipo.yaml com nome, papéis, seções da spec e validadores
- cada papel aponta para um agente que existe em .claude/agents/
- cada validador aponta para um script que existe
- AGENTS.tipo.md e os templates spec/design/entrega existem
- o template da spec tem todas as seções obrigatórias
"""
from __future__ import annotations

import re
import shlex
import sys

from _common import ROOT, relatar

PAPEIS = ("especificacao", "design", "orquestracao", "documentacao")


def main() -> int:
    erros: list[str] = []
    caminho = ROOT / ".squad" / "tipo.yaml"
    if not caminho.exists():
        return relatar("tipo", [".squad/tipo.yaml ausente"])
    import yaml  # type: ignore

    t = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    for campo in ("tipo", "nome", "papeis", "spec", "validadores"):
        if not t.get(campo):
            erros.append(f".squad/tipo.yaml: campo obrigatório ausente: {campo}")
    for papel in PAPEIS:
        agente = (t.get("papeis") or {}).get(papel)
        if not agente:
            erros.append(f".squad/tipo.yaml: papel '{papel}' sem agente")
        elif not (ROOT / ".claude" / "agents" / f"{agente}.md").exists():
            erros.append(f"papel '{papel}' aponta para .claude/agents/{agente}.md, que não existe")
    for v in t.get("validadores") or []:
        partes = shlex.split(v.get("cmd", ""))
        script = next((p for p in partes if p.endswith(".py")), None)
        if script and not (ROOT / script).exists():
            erros.append(f"validador '{v.get('nome')}' usa {script}, que não existe")
    for arq in ("AGENTS.tipo.md", "templates/spec.md", "templates/design.md", "templates/entrega.md", "templates/tasks.md"):
        if not (ROOT / arq).exists():
            erros.append(f"{arq} ausente")
    spec = ROOT / "templates" / "spec.md"
    if spec.exists():
        texto = spec.read_text(encoding="utf-8")
        for secao in (t.get("spec") or {}).get("secoes") or []:
            if not re.search(rf"^## .*{re.escape(secao)}", texto, re.M):
                erros.append(f"templates/spec.md não tem a seção obrigatória '{secao}'")
    for ag in (ROOT / ".claude" / "agents").glob("*.md"):
        cab = ag.read_text(encoding="utf-8").split("---")
        if len(cab) < 3 or f"name: {ag.stem}" not in cab[1] or "description:" not in cab[1]:
            erros.append(f"{ag.relative_to(ROOT)}: front matter precisa de name: {ag.stem} e description")
    return relatar("tipo", erros)


if __name__ == "__main__":
    sys.exit(main())
