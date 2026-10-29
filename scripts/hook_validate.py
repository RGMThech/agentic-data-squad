#!/usr/bin/env python3
"""Hook PostToolUse: valida o arquivo recém-editado pelo agente.

Recebe o evento em JSON pelo stdin. Se a validação falhar, sai com código 2 e
escreve o motivo no stderr — o agente recebe a mensagem e deve corrigir antes
de seguir.
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_contracts  # noqa: E402
import check_spec  # noqa: E402
import validate_naming  # noqa: E402
from _common import ROOT  # noqa: E402


def main() -> int:
    try:
        evento = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    caminho = (evento.get("tool_input") or {}).get("file_path")
    if not caminho:
        return 0
    p = Path(caminho).resolve()
    try:
        topo = p.relative_to(ROOT).parts[0]
    except (ValueError, IndexError):
        return 0

    verificacoes = []
    if topo in {"pipelines", "contracts", "specs"}:
        verificacoes.append(lambda: validate_naming.main([str(p)]))
    if topo in {"pipelines", "contracts"}:
        verificacoes.append(check_contracts.main)
    if topo == "specs":
        verificacoes.append(check_spec.main)

    saida = io.StringIO()
    falhou = False
    with redirect_stdout(io.StringIO()), redirect_stderr(saida):
        for v in verificacoes:
            falhou |= v() != 0

    if falhou:
        print("Harness bloqueou a alteração. Corrija antes de continuar:", file=sys.stderr)
        print(saida.getvalue(), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
