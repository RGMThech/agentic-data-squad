-- Validação de negócio da feature 000 — o Operador roda e confere com um número conhecido.
-- Ex.: o fechamento do ERP de ontem para a loja L01.

SELECT
    loja_cd,
    venda_dt,
    pedidos_qt,
    receita_liquida_vl,
    ticket_medio_vl
FROM gld_vendas__receita_diaria_loja
WHERE venda_dt = CURRENT_DATE - INTERVAL '1' DAY
ORDER BY receita_liquida_vl DESC;
