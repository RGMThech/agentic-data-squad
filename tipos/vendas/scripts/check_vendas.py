#!/usr/bin/env python3
"""Validador da squad de vendas.

- cadências (cadencias/**/*.md): campos; e-mail com assunto até 60, corpo até 180 palavras e descadastro
- propostas (propostas/**/*.md): cliente, validade (AAAA-MM-DD), valor_total, condicoes_pagamento, status
- contas e cadências sem CPF nem e-mail pessoal
- nenhum material usa promessa proibida em docs/oferta.md
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from _common import ROOT, ler_documento, procurar_pii, relatar

CANAIS = {"email", "linkedin", "ligacao", "whatsapp"}
STATUS = {"rascunho", "em_revisao", "aprovado"}
RE_DESCADASTRO = re.compile(r"descadastr|\bsair\b|n[aã]o (quiser|quer) (mais )?receber|remover (seu|o seu|meu)? ?(contato|e-?mail)|opt-?out|unsubscribe", re.I)
RE_EMAIL_PESSOAL = re.compile(r"\b[\w.+-]+@(gmail|hotmail|outlook|live|yahoo|icloud|bol|uol|terra|ig)\.com(\.br)?\b", re.I)
PASTAS_MATERIAIS = ("cadencias", "propostas", "apresentacoes", "playbooks")


def promessas_proibidas(raiz: Path) -> list[str]:
    oferta = raiz / "docs" / "oferta.md"
    if not oferta.exists():
        return []
    m = re.search(r"^##\s+Promessas proibidas\s*$(.*?)(?=^##\s|\Z)", oferta.read_text(encoding="utf-8"), re.M | re.S | re.I)
    return [t.strip() for t in re.findall(r"^\s*-\s+(.+)$", m.group(1), re.M) if t.strip() and not t.strip().startswith("<")] if m else []


def corpo_limpo(corpo: str) -> str:
    return re.sub(r"<!--.*?-->", "", corpo, flags=re.S).strip()


def checar_passo(arq: Path, raiz: Path) -> list[str]:
    rel = arq.relative_to(raiz)
    meta, corpo = ler_documento(arq)
    if not meta:
        return [f"{rel}: sem front matter (use templates/passo-cadencia.md)"]
    erros = [f"{rel}: campo obrigatório vazio: {c}" for c in ("passo", "dia", "canal") if meta.get(c) in (None, "")]
    canal = str(meta.get("canal") or "").lower()
    if canal and canal not in CANAIS:
        erros.append(f"{rel}: canal '{canal}' desconhecido ({', '.join(sorted(CANAIS))})")
    if canal == "email":
        assunto = str(meta.get("assunto") or "")
        if not assunto:
            erros.append(f"{rel}: e-mail sem 'assunto'")
        elif len(assunto) > 60:
            erros.append(f"{rel}: assunto com {len(assunto)} caracteres (limite 60)")
        texto = corpo_limpo(corpo)
        palavras = len(texto.split())
        if palavras > 180:
            erros.append(f"{rel}: corpo com {palavras} palavras (limite 180)")
        if not RE_DESCADASTRO.search(texto):
            erros.append(f"{rel}: e-mail sem linha de descadastro")
    return erros


def checar_proposta(arq: Path, raiz: Path) -> list[str]:
    rel = arq.relative_to(raiz)
    meta, _ = ler_documento(arq)
    erros = [f"{rel}: campo obrigatório vazio: {c}" for c in ("cliente", "validade", "valor_total", "condicoes_pagamento", "status") if meta.get(c) in (None, "")]
    v = meta.get("validade")
    if v not in (None, "") and not isinstance(v, date):
        try:
            date.fromisoformat(str(v))
        except ValueError:
            erros.append(f"{rel}: validade '{v}' não está no formato AAAA-MM-DD")
    if meta.get("status") and meta["status"] not in STATUS:
        erros.append(f"{rel}: status '{meta['status']}' inválido ({' | '.join(sorted(STATUS))})")
    return erros


def checar(raiz: Path = ROOT) -> list[str]:
    erros: list[str] = []
    for arq in sorted((raiz / "cadencias").rglob("*.md")):
        if arq.name.lower() != "readme.md":
            erros += checar_passo(arq, raiz)
    for arq in sorted((raiz / "propostas").rglob("*.md")):
        if arq.name.lower() != "readme.md":
            erros += checar_proposta(arq, raiz)
    for pasta in ("contas", "cadencias"):
        for arq in sorted((raiz / pasta).rglob("*")):
            if not arq.is_file() or arq.suffix.lower() not in (".md", ".txt", ".csv", ".yaml", ".yml", ".json"):
                continue
            texto = arq.read_text(encoding="utf-8", errors="ignore")
            achados = procurar_pii(texto, ("CPF",)) + (["e-mail pessoal"] if RE_EMAIL_PESSOAL.search(texto) else [])
            if achados:
                erros.append(f"{arq.relative_to(raiz)}: dado pessoal na prospecção ({', '.join(achados)}). Use só dados corporativos.")
    proibidas = promessas_proibidas(raiz)
    for pasta in PASTAS_MATERIAIS:
        for arq in sorted((raiz / pasta).rglob("*.md")):
            texto = arq.read_text(encoding="utf-8", errors="ignore").lower()
            for termo in proibidas:
                if termo.lower() in texto:
                    erros.append(f"{arq.relative_to(raiz)}: promessa proibida: '{termo}' (docs/oferta.md)")
    return erros


if __name__ == "__main__":
    sys.exit(relatar("vendas", checar()))
