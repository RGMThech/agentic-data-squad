from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_produto  # noqa: E402

ITEM = """feature: 001-x
itens:
  - id: HU-01
    titulo: Pagar com Pix
    historia: Como cliente, quero pagar com Pix, para concluir a compra sem cartão.
    rice: {alcance: 1000, impacto: 2, confianca: 0.8, esforco: 2}
    rice_score: %s
"""


def test_repositorio_vazio_passa(tmp_path):
    assert check_produto.checar(tmp_path) == []


def test_rice_consistente(tmp_path):
    (tmp_path / "backlog").mkdir()
    (tmp_path / "backlog" / "001-x.yaml").write_text(ITEM % 800, encoding="utf-8")
    assert check_produto.checar(tmp_path) == []
    (tmp_path / "backlog" / "001-x.yaml").write_text(ITEM % 50, encoding="utf-8")
    assert any("não bate" in e for e in check_produto.checar(tmp_path))


def test_prd_precisa_de_secoes_e_historias(tmp_path):
    d = tmp_path / "specs" / "001-x"
    d.mkdir(parents=True)
    (d / "design.md").write_text("---\nstatus: em_revisao\n---\n## Escopo\n", encoding="utf-8")
    erros = check_produto.checar(tmp_path)
    assert any("Plano de lançamento" in e for e in erros) and any("história" in e for e in erros)


def test_pesquisa_sem_dados_pessoais(tmp_path):
    p = tmp_path / "pesquisa" / "001-x"
    p.mkdir(parents=True)
    (p / "sintese.md").write_text("P1 disse que o cadastro é longo.", encoding="utf-8")
    assert check_produto.checar(tmp_path) == []
    (p / "sintese.md").write_text("Maria (maria.souza@empresa.com.br) disse que…", encoding="utf-8")
    assert any("dado pessoal" in e for e in check_produto.checar(tmp_path))
