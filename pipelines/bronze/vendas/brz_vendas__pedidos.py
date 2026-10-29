"""brz_vendas__pedidos — ingestão dos pedidos do ERP (exemplo).

Spec:   specs/000-exemplo-receita-diaria/spec.md
Design: specs/000-exemplo-receita-diaria/design.md (§2, §4)

Bronze preserva o dado como veio da fonte e acrescenta colunas técnicas.
Nenhuma regra de negócio é aplicada aqui.
"""
from __future__ import annotations

from datetime import datetime, timezone

TABELA_DESTINO = "brz_vendas__pedidos"
FONTE_CD = "ERP"
COLUNAS_TECNICAS = ("_ingestao_ts", "_fonte_cd", "_lote_id")


def extrair(desde: datetime):
    """Extrai pedidos alterados desde `desde`.

    # PLATAFORMA: substitua pela leitura real (JDBC, API, arquivos em object storage,
    # Auto Loader, Fivetran, Airbyte...). Credenciais SEMPRE via gerenciador de segredos.
    """
    raise NotImplementedError("Implementar a extração para a sua plataforma")


def enriquecer(registros: list[dict], lote_id: int) -> list[dict]:
    """Acrescenta as colunas técnicas obrigatórias da bronze."""
    agora = datetime.now(timezone.utc).isoformat()
    return [
        {**r, "_ingestao_ts": agora, "_fonte_cd": FONTE_CD, "_lote_id": lote_id}
        for r in registros
    ]


def gravar(registros: list[dict], lote_id: int) -> None:
    """Grava o lote em modo append de forma idempotente.

    Idempotência: antes de gravar, remova (ou ignore) registros já existentes
    com o mesmo `_lote_id`, para que reexecutar o lote não duplique dados.

    # PLATAFORMA: ex.: DELETE WHERE _lote_id = ? + INSERT, ou MERGE por (_lote_id, pedido_id).
    """
    raise NotImplementedError("Implementar a gravação para a sua plataforma")


def executar(desde: datetime, lote_id: int) -> None:
    registros = extrair(desde)
    gravar(enriquecer(registros, lote_id), lote_id)
