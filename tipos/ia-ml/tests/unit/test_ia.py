from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_ia  # noqa: E402

EVAL = """modelo: churn-v1
dataset: teste-2026-09
metricas:
  - {nome: recall, valor: %s, limiar: 0.85, direcao: maior}
  - {nome: latencia_p95_ms, valor: 300, limiar: 800, direcao: menor}
resultado: aprovado
"""


def test_repositorio_vazio_passa(tmp_path):
    assert check_ia.checar(tmp_path) == []


def test_eval_coerente(tmp_path):
    d = tmp_path / "avaliacoes" / "001-churn"
    d.mkdir(parents=True)
    (d / "eval.yaml").write_text(EVAL % 0.9, encoding="utf-8")
    assert check_ia.checar(tmp_path) == []
    (d / "eval.yaml").write_text(EVAL % 0.7, encoding="utf-8")
    assert any("abaixo do limiar: recall" in e for e in check_ia.checar(tmp_path))


def test_model_card_incompleto(tmp_path):
    d = tmp_path / "modelos" / "churn"
    d.mkdir(parents=True)
    (d / "model-card.md").write_text("# Card\n## Visão geral\nx\n", encoding="utf-8")
    assert any("Limitações e riscos" in e for e in check_ia.checar(tmp_path))


def test_prompt_sem_dado_pessoal(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "atendente.md").write_text("Exemplo: cliente com CPF 123.456.789-09", encoding="utf-8")
    assert any("dado pessoal" in e for e in check_ia.checar(tmp_path))
