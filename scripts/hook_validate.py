#!/usr/bin/env python3
"""Hook PostToolUse: valida o arquivo recém-editado pelo agente.

Recebe o evento em JSON pelo stdin e roda os validadores do tipo da squad que se
aplicam ao arquivo (.squad/tipo.yaml). Se algum falhar, sai com código 2 e escreve
o motivo no stderr: o agente recebe a mensagem e deve corrigir antes de seguir.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        evento = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    caminho = (evento.get("tool_input") or {}).get("file_path")
    if not caminho:
        return 0
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gates.py"), "--arquivo", caminho], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print("Harness bloqueou a alteração. Corrija antes de continuar:", file=sys.stderr)
        print((r.stdout + r.stderr)[-4000:], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
