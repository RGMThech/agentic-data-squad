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


def test_status_de_tarefa_com_observacoes():
    assert check_spec.status_tarefa("aprovado (QA; bronze executada)") == ("aprovado", "QA; bronze executada")
    assert check_spec.status_tarefa("`em_qa`") == ("em_qa", "")
    assert check_spec.status_tarefa("nao_executar — fora do escopo")[0] == "nao_executar"
    assert check_spec.status_tarefa("Resolvido fora — feito pelo DBA") == ("resolvido_fora", "feito pelo DBA")


def test_g3_exige_tarefas_encerradas(tmp_path, monkeypatch):
    pasta = tmp_path / "specs" / "001-x"
    pasta.mkdir(parents=True)
    fm = "---\nstatus: aprovado\naprovado_por: a\naprovado_em: 2026-11-02\n---\n"
    (pasta / "spec.md").write_text(fm, encoding="utf-8")
    (pasta / "design.md").write_text(fm, encoding="utf-8")
    tabela = "| ID | Tarefa | Status |\n|---|---|---|\n| T-01 | a | aprovado |\n| T-02 | b | {s} |\n"
    monkeypatch.setattr(check_spec, "ROOT", tmp_path)
    (pasta / "tasks.md").write_text(tabela.format(s="pendente"), encoding="utf-8")
    assert check_spec.checar_g3("001-x") == 1
    (pasta / "tasks.md").write_text(tabela.format(s="nao_executar"), encoding="utf-8")
    assert check_spec.checar_g3("001-x") == 1, "sem justificativa"
    (pasta / "tasks.md").write_text(tabela.format(s="nao_executar — fora do escopo"), encoding="utf-8")
    assert check_spec.checar_g3("001-x") == 0
