from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_software  # noqa: E402


def _spec(raiz, status, corpo, nome="spec.md"):
    p = raiz / "specs" / "001-x" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\nstatus: {status}\n---\n{corpo}", encoding="utf-8")


def test_repositorio_vazio_passa(tmp_path):
    assert check_software.checar(tmp_path) == []


def test_exige_historia_de_usuario(tmp_path):
    _spec(tmp_path, "em_revisao", "## Histórias de usuário\n- quero um botão\n")
    assert any("história" in e for e in check_software.checar(tmp_path))
    _spec(tmp_path, "em_revisao", "## Histórias de usuário\n- Como cliente, quero pagar com Pix, para não usar cartão.\n")
    assert check_software.checar(tmp_path) == []


def test_rascunho_nao_e_cobrado(tmp_path):
    _spec(tmp_path, "rascunho", "nada ainda")
    assert check_software.checar(tmp_path) == []


def test_design_precisa_das_secoes(tmp_path):
    _spec(tmp_path, "em_revisao", "## 1. Visão da solução\n", "design.md")
    erros = check_software.checar(tmp_path)
    assert any("Estratégia de testes" in e for e in erros)


def test_detecta_segredo_no_codigo(tmp_path):
    (tmp_path / "src").mkdir()
    segredo = "API_KEY = " + chr(34) + "abcd1234" + "efgh5678" + chr(34)  # montado para o próprio teste não ser apontado
    (tmp_path / "src" / "config.py").write_text(segredo + "\n", encoding="utf-8")
    assert any("segredo" in e for e in check_software.checar(tmp_path))
    (tmp_path / "src" / "config.py").write_text('API_KEY = os.environ["API_KEY"]\n', encoding="utf-8")
    assert check_software.checar(tmp_path) == []
