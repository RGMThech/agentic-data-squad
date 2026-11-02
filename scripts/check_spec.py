#!/usr/bin/env python3
"""Garante que nenhuma feature avance sem os gates G1/G2.

Regras:
- spec.md e design.md têm front matter com 'status' válido
- spec 'aprovado' não pode ter dúvidas abertas ("- [ ]" na seção Dúvidas abertas)
  e precisa de aprovado_por/aprovado_em
- design.md só pode estar 'aprovado' se a spec estiver aprovada
  (quando a spec muda depois do G1, spec e design voltam a 'em_revisao' juntos)
- tasks.md não pode existir com a spec ainda em rascunho

Modo G3 (PR pronto para produção):
  python scripts/check_spec.py --g3 <feature>
  exige spec e design aprovados e todas as tarefas encerradas:
  aprovado, nao_executar ou resolvido_fora (os dois últimos com justificativa).
"""
from __future__ import annotations

import re
import sys

from _common import ROOT, ler_frontmatter, relatar

STATUS = {"rascunho", "em_revisao", "aprovado"}
FINAIS = {"aprovado", "nao_executar", "resolvido_fora"}
ALIAS = [
    (r"^(aprovad[oa]|conclu[ií]d[oa]|feit[oa])\b", "aprovado"),
    (r"^(n[aã]o[ _-]?executar|n[aã]o ser[aá] executad[oa]|cancelad[oa])\b", "nao_executar"),
    (r"^(resolvid[oa][ _-]?(fora|de outra forma))\b", "resolvido_fora"),
]


def status_tarefa(celula: str) -> tuple[str, str]:
    """('aprovado', 'nota') a partir de células como 'aprovado (QA ok)' ou 'nao_executar — motivo'."""
    limpo = celula.replace("`", "").strip()
    baixo = limpo.lower()
    for padrao, st in ALIAS:
        m = re.match(padrao, baixo)
        if m:
            return st, limpo[m.end():].strip(" ()—–:-")
    return (baixo.split() or [""])[0], ""


def tarefas(caminho) -> list[tuple[str, str, str]]:
    """[(id, status, nota)] da tabela de tarefas."""
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    try:
        ih = next(i for i, l in enumerate(linhas) if re.match(r"^\|\s*ID\s*\|", l, re.I) and "status" in l.lower())
    except StopIteration:
        return []
    cab = [c.strip().lower() for c in linhas[ih].strip().strip("|").split("|")]
    i_id = next(i for i, c in enumerate(cab) if c.startswith("id"))
    i_st = next(i for i, c in enumerate(cab) if c.startswith("status"))
    out = []
    for l in linhas[ih + 2:]:
        if not l.strip().startswith("|"):
            break
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) > max(i_id, i_st) and re.match(r"^T-\d+", c[i_id], re.I):
            out.append((c[i_id], *status_tarefa(c[i_st])))
    return out


def checar_g3(feature: str) -> int:
    pasta = ROOT / "specs" / feature
    erros: list[str] = []
    if not pasta.is_dir():
        return relatar("G3", [f"specs/{feature}: feature não encontrada"])
    for nome in ("spec.md", "design.md"):
        arq = pasta / nome
        if not arq.exists() or ler_frontmatter(arq).get("status") != "aprovado":
            erros.append(f"specs/{feature}/{nome}: precisa estar aprovado para o G3")
    t = pasta / "tasks.md"
    if not t.exists():
        erros.append(f"specs/{feature}/tasks.md: ausente")
    else:
        for tid, st, nota in tarefas(t):
            if st not in FINAIS:
                erros.append(f"{tid}: status '{st}' — conclua, reexecute ou marque como nao_executar / resolvido_fora")
            elif st != "aprovado" and len(nota) < 5:
                erros.append(f"{tid}: '{st}' precisa de justificativa")
    return relatar("G3", erros)
SECOES_PADRAO = ["Critérios de aceite", "Dúvidas abertas"]


def secoes_spec() -> list[str]:
    """Seções obrigatórias da spec para o tipo desta squad (.squad/tipo.yaml → spec.secoes)."""
    caminho = ROOT / ".squad" / "tipo.yaml"
    try:
        import yaml  # type: ignore

        dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
        return list((dados.get("spec") or {}).get("secoes") or SECOES_PADRAO)
    except Exception:
        return SECOES_PADRAO


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
    if ops and fm.get("exemplo") != "true" and fm["aprovado_por"].strip().lstrip("@").lower() not in ops:
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
    return {str(o).strip().lstrip("@").lower() for o in (dados.get("operadores") or [])}


def main() -> int:
    erros: list[str] = []
    pastas = (ROOT / "specs").iterdir() if (ROOT / "specs").is_dir() else []
    for pasta in sorted(p for p in pastas if p.is_dir()):
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
        for secao in secoes_spec():
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
            if status_design == "aprovado" and status_spec != "aprovado":
                erros.append(f"{reld}: design aprovado com a spec fora de aprovação (reabra o G2 junto com o G1)")
            erros += checar_aprovacao(reld, fmd)

        if tasks.exists() and status_spec == "rascunho":
            erros.append(f"{tasks.relative_to(ROOT)}: tarefas criadas com a spec em rascunho")

    return relatar("specs/gates", erros)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--g3":
        sys.exit(checar_g3(sys.argv[2]))
    sys.exit(main())
