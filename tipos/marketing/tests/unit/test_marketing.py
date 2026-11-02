from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_marketing  # noqa: E402

BASE = "objetivo: gerar leads\npublico: PMEs\ncta: Saiba mais\nstatus: em_revisao\nformato: post\n"


def _peca(raiz, nome, fm, corpo="Texto curto."):
    p = raiz / "pecas" / "001-lancamento" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\n{fm}---\n{corpo}\n", encoding="utf-8")


def test_repositorio_vazio_passa(tmp_path):
    assert check_marketing.checar(tmp_path) == []


def test_peca_valida(tmp_path):
    _peca(tmp_path, "linkedin-post.md", "canal: linkedin\n" + BASE + "url: https://x.com.br/?utm_source=linkedin&utm_medium=social&utm_campaign=001-lancamento\n")
    assert check_marketing.checar(tmp_path) == []


def test_limite_do_canal_x(tmp_path):
    _peca(tmp_path, "x-post.md", "canal: x\n" + BASE, "a" * 281)
    assert any("280" in e for e in check_marketing.checar(tmp_path))


def test_link_sem_utm(tmp_path):
    _peca(tmp_path, "x-post.md", "canal: x\n" + BASE + "url: https://x.com.br/oferta\n")
    assert any("utm_campaign" in e for e in check_marketing.checar(tmp_path))


def test_campos_e_google_ads(tmp_path):
    _peca(tmp_path, "ads.md", "canal: google-ads\n" + BASE + "titulos: [Um título que é longo demais para o google]\ndescricoes: [ok]\n")
    erros = check_marketing.checar(tmp_path)
    assert any("30 caracteres" in e for e in erros)
    _peca(tmp_path, "ads.md", "canal: email\nstatus: aprovado\n")
    erros = check_marketing.checar(tmp_path)
    assert any("assunto" in e for e in erros) and any("cta" in e for e in erros)


def test_termo_proibido(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "marca.md").write_text("# Marca\n\n## Termos e promessas proibidos\n- risco zero\n\n## Outra\n- ok\n", encoding="utf-8")
    _peca(tmp_path, "x-post.md", "canal: x\n" + BASE, "Invista com RISCO ZERO!")
    assert any("risco zero" in e for e in check_marketing.checar(tmp_path))
