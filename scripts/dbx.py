#!/usr/bin/env python3
"""Compatibilidade: use scripts/dados.py (acesso a dados em qualquer plataforma da squad)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dados import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
