"""Testes dos próprios validadores do harness."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import RE_COLUNA, RE_TABELA  # noqa: E402
import check_spec  # noqa: E402


def test_nomes_de_tabela_validos():
    for nome in ["slv_vendas__pedidos", "gld_vendas__receita_diaria_loja", "brz_credito__score2"]:
        assert RE_TABELA.match(nome), nome


def test_nomes_de_tabela_invalidos():
    for nome in ["slv_vendas_pedidos", "Slv_vendas__pedidos", "stg_vendas__pedidos", "gld_vendas__Receita", "gld_v__x"]:
        assert not RE_TABELA.match(nome), nome


def test_colunas():
    assert RE_COLUNA.match("receita_bruta_vl")
    assert RE_COLUNA.match("_ingestao_ts")
    assert not RE_COLUNA.match("ReceitaBruta")
    assert not RE_COLUNA.match("receita-bruta")
    assert not RE_COLUNA.match("preço_vl")


def test_detecta_duvidas_abertas():
    texto = "## 11. Dúvidas abertas\n- [ ] qual fuso?\n- [x] resolvida\n\n## 12. Decisões\n- [ ] não conta\n"
    assert check_spec.duvidas_abertas(texto) == ["- [ ] qual fuso?"]
