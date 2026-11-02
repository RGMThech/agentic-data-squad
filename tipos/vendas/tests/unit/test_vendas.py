from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_vendas  # noqa: E402


def _arq(raiz, caminho, texto):
    p = raiz / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def test_repositorio_vazio_passa(tmp_path):
    assert check_vendas.checar(tmp_path) == []


def test_email_de_cadencia(tmp_path):
    ok = "---\npasso: 1\ndia: 0\ncanal: email\nassunto: Ideia para reduzir paradas na linha\n---\nOlá. Texto curto.\nSe não quiser mais receber, responda sair.\n"
    _arq(tmp_path, "cadencias/001-x/1-email.md", ok)
    assert check_vendas.checar(tmp_path) == []
    longo = ok.replace("Texto curto.", "palavra " * 200).replace("Se não quiser mais receber, responda sair.", "")
    _arq(tmp_path, "cadencias/001-x/1-email.md", longo)
    erros = check_vendas.checar(tmp_path)
    assert any("180" in e for e in erros) and any("descadastro" in e for e in erros)


def test_proposta(tmp_path):
    _arq(tmp_path, "propostas/001-x/acme.md", "---\ncliente: ACME\nvalidade: 31/12/2026\nvalor_total: R$ 10.000\nstatus: em_revisao\n---\n# Proposta\n")
    erros = check_vendas.checar(tmp_path)
    assert any("condicoes_pagamento" in e for e in erros) and any("AAAA-MM-DD" in e for e in erros)


def test_dados_pessoais_e_promessas(tmp_path):
    _arq(tmp_path, "contas/001-x/acme.md", "Diretora de Operações: joana.silva@gmail.com")
    _arq(tmp_path, "docs/oferta.md", "# Oferta\n## Promessas proibidas\n- retorno garantido\n")
    _arq(tmp_path, "playbooks/001-x.md", "Prometa RETORNO GARANTIDO em 30 dias.")
    erros = check_vendas.checar(tmp_path)
    assert any("e-mail pessoal" in e for e in erros) and any("retorno garantido" in e for e in erros)
