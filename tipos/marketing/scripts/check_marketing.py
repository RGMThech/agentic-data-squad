#!/usr/bin/env python3
"""Validador da squad de marketing.

- peças (pecas/**/*.md): campos obrigatórios, status válido, limites por canal, UTMs nos links
- nenhuma peça usa termo ou promessa proibida em docs/marca.md
- plano de campanha (design.md) em revisão ou aprovado tem as seções obrigatórias
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from _common import ROOT, faltando_secoes, ler_documento, relatar

CAMPOS = ("canal", "formato", "objetivo", "publico", "cta", "status")
STATUS = {"rascunho", "em_revisao", "aprovado"}
LIMITE_TEXTO = {"x": 280, "linkedin": 3000, "instagram": 2200, "facebook": 5000, "tiktok": 2200, "youtube": 5000, "meta-ads": 2200, "whatsapp": 1024}
CANAIS = set(LIMITE_TEXTO) | {"email", "blog", "landing-page", "google-ads"}
LIMITE_CAMPO = {"assunto": 60, "pre_header": 100, "titulo_seo": 60, "meta_descricao": 160}
SECOES_PLANO = ["Conceito criativo", "Peças", "Calendário", "Mensuração"]
UTMS = ("utm_source", "utm_medium", "utm_campaign")


def termos_proibidos(raiz: Path) -> list[str]:
    marca = raiz / "docs" / "marca.md"
    if not marca.exists():
        return []
    texto = marca.read_text(encoding="utf-8")
    m = re.search(r"^##\s+Termos e promessas proibidos\s*$(.*?)(?=^##\s|\Z)", texto, re.M | re.S | re.I)
    if not m:
        return []
    return [t.strip().strip("`\"") for t in re.findall(r"^\s*-\s+(.+)$", m.group(1), re.M) if t.strip() and not t.strip().startswith("<")]


def texto_da_peca(corpo: str) -> str:
    return re.sub(r"<!--.*?-->", "", corpo, flags=re.S).strip()


def checar_peca(arq: Path, raiz: Path, proibidos: list[str]) -> list[str]:
    rel = arq.relative_to(raiz)
    meta, corpo = ler_documento(arq)
    if not meta:
        return [f"{rel}: sem front matter (use templates/peca.md)"]
    erros = [f"{rel}: campo obrigatório vazio: {c}" for c in CAMPOS if not str(meta.get(c) or "").strip()]
    canal = str(meta.get("canal") or "").lower()
    if canal and canal not in CANAIS:
        erros.append(f"{rel}: canal '{canal}' desconhecido ({', '.join(sorted(CANAIS))})")
    if meta.get("status") and meta["status"] not in STATUS:
        erros.append(f"{rel}: status '{meta['status']}' inválido ({' | '.join(sorted(STATUS))})")
    texto = texto_da_peca(corpo)
    if canal in LIMITE_TEXTO and len(texto) > LIMITE_TEXTO[canal]:
        erros.append(f"{rel}: texto com {len(texto)} caracteres; limite do canal {canal} é {LIMITE_TEXTO[canal]}")
    if canal == "email" and not meta.get("assunto"):
        erros.append(f"{rel}: e-mail sem 'assunto'")
    for campo, lim in LIMITE_CAMPO.items():
        v = str(meta.get(campo) or "")
        if len(v) > lim:
            erros.append(f"{rel}: '{campo}' com {len(v)} caracteres (limite {lim})")
    if canal == "google-ads":
        titulos, descricoes = meta.get("titulos") or [], meta.get("descricoes") or []
        if not titulos or not descricoes:
            erros.append(f"{rel}: anúncio do Google Ads precisa de 'titulos' e 'descricoes'")
        if len(titulos) > 15 or len(descricoes) > 4:
            erros.append(f"{rel}: Google Ads aceita até 15 títulos e 4 descrições")
        erros += [f"{rel}: título '{t}' passa de 30 caracteres" for t in titulos if len(str(t)) > 30]
        erros += [f"{rel}: descrição passa de 90 caracteres: '{str(d)[:40]}…'" for d in descricoes if len(str(d)) > 90]
    url = str(meta.get("url") or "")
    if url:
        faltam = [u for u in UTMS if u not in parse_qs(urlparse(url).query)]
        if faltam:
            erros.append(f"{rel}: link sem {', '.join(faltam)}")
    alvo = " ".join([texto] + [str(v) for v in meta.values()]).lower()
    for termo in proibidos:
        if termo.lower() in alvo:
            erros.append(f"{rel}: usa termo proibido pela marca: '{termo}' (docs/marca.md)")
    return erros


def checar(raiz: Path = ROOT) -> list[str]:
    erros: list[str] = []
    proibidos = termos_proibidos(raiz)
    for arq in sorted((raiz / "pecas").rglob("*.md")):
        if arq.name.lower() == "readme.md" or arq.name.startswith("arte-"):
            continue
        erros += checar_peca(arq, raiz, proibidos)
    for design in sorted((raiz / "specs").glob("*/design.md")):
        meta, corpo = ler_documento(design)
        if meta.get("status") in ("em_revisao", "aprovado"):
            erros += [f"{design.relative_to(raiz)}: falta a seção '{s}'" for s in faltando_secoes(corpo, SECOES_PLANO)]
    return erros


if __name__ == "__main__":
    sys.exit(relatar("marketing", checar()))
