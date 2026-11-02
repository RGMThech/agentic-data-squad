#!/usr/bin/env python3
"""Transforma uma cópia do template numa squad de um tipo (dados, software, marketing…).

Uso:
  python scripts/instanciar_tipo.py <tipo> [--raiz <pasta>]

O Squad Console faz o mesmo direto no GitHub (um único commit) ao criar a squad;
este script serve para uso local e para o CI do template testar cada tipo.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def casa(path: str, padroes: list[str]) -> bool:
    return any(path == p or (p.endswith("/**") and path.startswith(p[:-2])) for p in padroes)


def planejar(arquivos: list[str], base: dict, tipo: str) -> tuple[list[str], dict[str, str]]:
    """(caminhos a apagar, {destino: origem} a copiar) — mesma regra usada pelo console."""
    tipos = base.get("tipos") or {}
    if tipo not in tipos:
        raise SystemExit(f"Tipo desconhecido: {tipo}. Tipos: {', '.join(tipos)}")
    apagar = [a for a in arquivos if a.startswith("tipos/")]
    copiar: dict[str, str] = {}
    if tipo != base.get("padrao"):
        remover = base.get("especifico_do_padrao") or []
        apagar += [a for a in arquivos if not a.startswith("tipos/") and casa(a, remover)]
        prefixo = f"tipos/{tipo}/"
        for a in arquivos:
            if a.startswith(prefixo):
                copiar[a[len(prefixo):]] = a
        apagar = [a for a in apagar if a not in copiar]
    return sorted(set(apagar)), copiar


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    tipo = argv[0]
    raiz = Path(argv[argv.index("--raiz") + 1] if "--raiz" in argv else Path(__file__).resolve().parent.parent)
    import yaml  # type: ignore

    base = yaml.safe_load((raiz / "tipos" / "base.yaml").read_text(encoding="utf-8"))
    arquivos = [p.relative_to(raiz).as_posix() for p in raiz.rglob("*") if p.is_file() and ".git" not in p.relative_to(raiz).parts]
    apagar, copiar = planejar(arquivos, base, tipo)
    for destino, origem in copiar.items():
        alvo = raiz / destino
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raiz / origem, alvo)
    for a in apagar:
        (raiz / a).unlink(missing_ok=True)
    shutil.rmtree(raiz / "tipos", ignore_errors=True)
    # remove pastas que ficaram vazias
    for d in sorted((p for p in raiz.rglob("*") if p.is_dir() and ".git" not in p.parts), key=lambda p: len(p.parts), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    print(f"Squad do tipo '{tipo}' pronta: {len(copiar)} arquivo(s) do pacote, {len(apagar)} removido(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
