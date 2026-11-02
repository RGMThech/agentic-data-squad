#!/usr/bin/env python3
"""Validador da squad de software.

- spec em revisão ou aprovada: histórias no formato "Como…, quero…, para…"
- design em revisão ou aprovado: seções obrigatórias
- código, testes e infra sem segredos (chaves privadas, tokens, senhas fixas)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _common import RE_HISTORIA, ROOT, faltando_secoes, ler_documento, relatar

SECOES_DESIGN = ["Visão da solução", "Componentes afetados", "Interfaces e contratos", "Segurança", "Estratégia de testes", "Plano de entrega"]
PASTAS_CODIGO = ("src", "app", "infra", "tests")
SEGREDOS = {
    "chave privada": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "chave de acesso AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "token do GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "chave de API (sk-)": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "token do Slack": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "senha ou segredo fixo": re.compile(r"(?i)\b(password|passwd|senha|secret|api[_-]?key|token)\b\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"),
}
IGNORAR = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
BINARIOS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".woff", ".woff2", ".ttf", ".lock"}


def checar_specs(raiz: Path) -> list[str]:
    erros = []
    for spec in sorted((raiz / "specs").glob("*/spec.md")):
        meta, corpo = ler_documento(spec)
        if meta.get("status") in ("em_revisao", "aprovado") and not RE_HISTORIA.search(corpo):
            erros.append(f"{spec.relative_to(raiz)}: nenhuma história no formato 'Como <persona>, quero <ação>, para <benefício>'")
    for design in sorted((raiz / "specs").glob("*/design.md")):
        meta, corpo = ler_documento(design)
        if meta.get("status") in ("em_revisao", "aprovado"):
            for s in faltando_secoes(corpo, SECOES_DESIGN):
                erros.append(f"{design.relative_to(raiz)}: falta a seção '{s}'")
    return erros


def checar_segredos(raiz: Path) -> list[str]:
    erros = []
    for pasta in PASTAS_CODIGO:
        for arq in sorted((raiz / pasta).rglob("*")):
            if not arq.is_file() or arq.suffix.lower() in BINARIOS or IGNORAR & set(arq.relative_to(raiz).parts):
                continue
            try:
                texto = arq.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for nome, rx in SEGREDOS.items():
                if rx.search(texto):
                    erros.append(f"{arq.relative_to(raiz)}: possível {nome} no arquivo. Use variável de ambiente.")
    return erros


def checar(raiz: Path = ROOT) -> list[str]:
    return checar_specs(raiz) + checar_segredos(raiz)


if __name__ == "__main__":
    sys.exit(relatar("software", checar()))
