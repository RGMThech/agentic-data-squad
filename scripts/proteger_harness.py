#!/usr/bin/env python3
"""Protege o harness da squad contra alterações feitas por agentes.

Os agentes não podem mudar as próprias regras: scripts, workflows, configuração do
Claude, constituição, templates e configuração de testes. Mudanças nesses arquivos
são feitas pelo Operador (Squad Console → Configuração, ou PR humano).

Uso:
  python scripts/proteger_harness.py restaurar        # após o agente: desfaz mudanças em arquivos protegidos
  python scripts/proteger_harness.py verificar <base> # CI da branch squad/*: falha se a branch altera arquivos protegidos
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROTEGIDOS = [
    "scripts/*",
    ".github/*",
    ".claude/*",
    ".squad/*",
    "templates/*",
    "AGENTS.md",
    "CLAUDE.md",
    "pytest.ini",
    "requirements-dev.txt",
    "tests/unit/test_dados.py",
    "tests/unit/test_harness.py",
]


def protegido(path: str) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in PROTEGIDOS)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def alterados_no_trabalho() -> list[str]:
    """Arquivos alterados, apagados ou criados e ainda não commitados."""
    saida = _git("status", "--porcelain", "--untracked-files=all")
    paths = []
    for linha in saida.splitlines():
        p = linha[3:].split(" -> ")[-1].strip().strip('"')
        if p:
            paths.append(p)
    return sorted({p for p in paths if protegido(p)})


def restaurar() -> int:
    paths = alterados_no_trabalho()
    if not paths:
        print("Harness intacto.")
        return 0
    rastreados = set(_git("ls-files").splitlines())
    for p in paths:
        if p in rastreados:
            _git("checkout", "HEAD", "--", p)
        else:
            (ROOT / p).unlink(missing_ok=True)
    msg = (
        "⚠️ **O agente tentou alterar o harness e as mudanças foram desfeitas:** "
        + ", ".join(f"`{p}`" for p in paths)
        + ". Se uma regra ou trava está impedindo o trabalho, o agente deve registrar o bloqueio para o Operador."
    )
    print(msg)
    destino = os.environ.get("HARNESS_AVISO")
    if destino:
        Path(destino).write_text(msg + "\n", encoding="utf-8")
    return 0


def verificar(base: str) -> int:
    paths = [p for p in _git("diff", "--name-only", f"{base}...HEAD").splitlines() if protegido(p)]
    if not paths:
        print("✅ harness: nenhuma alteração em arquivos protegidos")
        return 0
    print("❌ harness: esta branch de feature altera arquivos protegidos (só o Operador muda o harness):")
    for p in paths:
        print(f"   - {p}")
    print("   Desfaça com: git checkout origin/main -- <arquivo>")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("restaurar", "verificar"):
        print(__doc__)
        sys.exit(2)
    sys.exit(restaurar() if sys.argv[1] == "restaurar" else verificar(sys.argv[2] if len(sys.argv) > 2 else "origin/main"))
