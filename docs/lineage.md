# Lineage

Mantido pelo agente `governanca-docs`.

## Vendas

```
ERP.pedidos
  └─► brz_vendas__pedidos                 (bronze, append)
        └─► slv_vendas__pedidos           (silver, 1 linha por pedido)
              └─► gld_vendas__receita_diaria_loja   (gold, loja × dia)
                    ├─► M-01 receita_bruta
                    ├─► M-02 receita_liquida
                    ├─► M-03 pedidos
                    └─► M-04 ticket_medio
                          └─► Painel Comercial (spec 000)
```
