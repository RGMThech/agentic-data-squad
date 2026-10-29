-- gld_vendas__receita_diaria_loja
-- Spec:     specs/000-exemplo-receita-diaria/spec.md
-- Contrato: contracts/gld_vendas__receita_diaria_loja.yaml
-- Grão:     1 linha por loja por dia com pelo menos um pedido válido
-- SQL ANSI. # PLATAFORMA: envolva em overwrite por partição (venda_dt) conforme sua engine.

SELECT
    loja_cd,
    pedido_dt                                                  AS venda_dt,
    COUNT(pedido_id)                                           AS pedidos_qt,          -- M-03
    CAST(SUM(valor_bruto_vl) AS DECIMAL(18, 2))                AS receita_bruta_vl,    -- M-01
    CAST(SUM(desconto_vl) AS DECIMAL(18, 2))                   AS desconto_vl,
    CAST(SUM(valor_bruto_vl - desconto_vl) AS DECIMAL(18, 2))  AS receita_liquida_vl,  -- M-02
    CAST(ROUND(SUM(valor_bruto_vl - desconto_vl) / COUNT(pedido_id), 2)
         AS DECIMAL(18, 2))                                    AS ticket_medio_vl      -- M-04, RN-04
FROM slv_vendas__pedidos
WHERE NOT cancelado_fl                                                                 -- RN-01
GROUP BY loja_cd, pedido_dt
