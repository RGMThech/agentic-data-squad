#!/usr/bin/env python3
"""Roda os validadores da squad definidos em .squad/tipo.yaml.

Uso:
  python scripts/gates.py                 # todos os validadores (CI e fim de cada tarefa)
  python scripts/gates.py --arquivo <p>   # só os que se aplicam a esse arquivo (hook pós-edição)
  python scripts/gates.py --listar        # mostra os validadores do tipo
"""
from __future__ import annotations

import fnmatch
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PADRAO = [{"nome": "Gates G1/G2", "cmd": "python scripts/check_spec.py", "arquivos": ["specs/**"]}]


def validadores() -> list[dict]:
    caminho = ROOT / ".squad" / "tipo.yaml"
    if not caminho.exists():
        return PADRAO
    try:
        import yaml  # type: ignore
    except ImportError:
        return PADRAO
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return dados.get("validadores") or PADRAO


def casa(path: str, padroes: list[str]) -> bool:
    return any(path == p or fnmatch.fnmatch(path, p) or (p.endswith("/**") and path.startswith(p[:-2])) for p in padroes)


def main(argv: list[str]) -> int:
    lista = validadores()
    if "--listar" in argv:
        for v in lista:
            print(f"- {v['nome']}: {v['cmd']}  (arquivos: {', '.join(v.get('arquivos') or ['*'])})")
        return 0
    if "--arquivo" in argv:
        alvo = argv[argv.index("--arquivo") + 1]
        p = Path(alvo).resolve()
        try:
            rel = p.relative_to(ROOT).as_posix()
        except ValueError:
            return 0
        lista = [v for v in lista if casa(rel, v.get("arquivos") or ["**"])]
    falhas = 0
    for v in lista:
        cmd = shlex.split(v["cmd"])
        if cmd and cmd[0] in ("python", "python3"):
            cmd[0] = sys.executable
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            falhas += 1
            print(f"❌ {v['nome']} falhou ({v['cmd']})", file=sys.stderr)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
