#!/usr/bin/env python3
"""CI do template: instancia cada tipo de squad numa pasta temporária e roda os validadores e os testes."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    import yaml  # type: ignore

    base = yaml.safe_load((ROOT / "tipos" / "base.yaml").read_text(encoding="utf-8"))
    rastreados = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    falhas = []
    for tipo in base["tipos"]:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "squad"
            for f in rastreados:
                if (ROOT / f).is_file():
                    (dest / f).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / f, dest / f)
            passos = [
                [sys.executable, "scripts/instanciar_tipo.py", tipo, "--raiz", str(dest)],
                [sys.executable, "scripts/check_tipo.py"],
                [sys.executable, "scripts/gates.py"],
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            ]
            for cmd in passos:
                r = subprocess.run(cmd, cwd=dest, capture_output=True, text=True)
                if r.returncode not in (0, 5):  # 5 = pytest sem testes
                    falhas.append(f"{tipo}: {' '.join(cmd[1:3])}\n{(r.stdout + r.stderr)[-2500:]}")
                    break
            else:
                print(f"✅ tipo {tipo}")
    for f in falhas:
        print(f"❌ {f}", file=sys.stderr)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
