-- slv_vendas__pedidos
-- Spec:     specs/000-exemplo-receita-diaria/spec.md
-- Contrato: contracts/slv_vendas__pedidos.yaml
-- Grão:     1 linha por pedido (versão mais recente)
-- SQL ANSI. # PLATAFORMA: envolva em MERGE/CREATE OR REPLACE conforme sua engine.

WITH versoes AS (
    SELECT
        b.*,
        -- RN-02: vale a versão mais recente recebida do pedido
        ROW_NUMBER() OVER (PARTITION BY b.pedido_id ORDER BY b._ingestao_ts DESC) AS _versao_rn
    FROM brz_vendas__pedidos AS b
)
SELECT
    pedido_id,
    loja_cd,
    cliente_id,
    pedido_ts,
    CAST(pedido_ts AS DATE)                      AS pedido_dt,     -- RN-03
    status_cd,
    status_cd = 'CANCELADO'                      AS cancelado_fl,  -- base para RN-01
    CAST(valor_bruto_vl AS DECIMAL(18, 2))       AS valor_bruto_vl,
    CAST(COALESCE(desconto_vl, 0) AS DECIMAL(18, 2)) AS desconto_vl,
    _ingestao_ts
FROM versoes
WHERE _versao_rn = 1
