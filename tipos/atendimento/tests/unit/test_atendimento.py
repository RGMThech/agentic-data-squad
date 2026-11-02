from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import check_atendimento  # noqa: E402


def _arq(raiz, caminho, texto):
    p = raiz / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def test_repositorio_vazio_passa(tmp_path):
    assert check_atendimento.checar(tmp_path) == []


def test_template_de_fluxo_e_valido(tmp_path):
    (tmp_path / "fluxos").mkdir()
    shutil.copy(RAIZ / "templates" / "fluxo.yaml", tmp_path / "fluxos" / "boleto.yaml")
    assert check_atendimento.checar(tmp_path) == []


def test_fluxo_sem_humano_e_com_beco(tmp_path):
    _arq(tmp_path, "fluxos/x.yaml", """inicio: a
nos:
  a: {tipo: pergunta, texto: Oi, opcoes: [{rotulo: B, proximo: b}, {rotulo: C, proximo: c}]}
  b: {tipo: mensagem, texto: Beco}
  c: {tipo: fim, texto: Tchau}
  d: {tipo: humano, texto: Solto}
""")
    erros = check_atendimento.checar(tmp_path)
    assert any("beco" in e for e in erros)
    assert any("inalcançáveis" in e and "d" in e for e in erros)
    assert any("humano" in e for e in erros)


def test_artigo_e_dado_pessoal(tmp_path):
    _arq(tmp_path, "kb/pagamentos/boleto.md", "---\ntitulo: Segunda via\ncategoria: pagamentos\npublico: cliente\nstatus: aprovado\nrevisado_em: 10/10/2026\n---\nLigue para (11) 98765-4321.\n")
    erros = check_atendimento.checar(tmp_path)
    assert any("AAAA-MM-DD" in e for e in erros) and any("dado de cliente" in e for e in erros)
