# ADR 0001 — Versão mais recente do pedido prevalece na silver

- **Data:** 2026-10-29
- **Status:** aceita
- **Feature:** specs/000-exemplo-receita-diaria

## Contexto
O ERP reenvia pedidos quando há correção (desconto, status). A bronze recebe todas as versões. A gold precisa refletir o estado atual de cada pedido.

## Opções consideradas
1. **Silver com a versão mais recente (SCD1)**: simples, atende a spec; perde o histórico na silver (mas ele continua na bronze).
2. **Silver com histórico (SCD2)**: permite análises de mudanças; mais custo e complexidade, sem demanda na spec.

## Decisão
Opção 1. A bronze preserva o histórico completo, então SCD2 pode ser criado depois sem perda de dado.

## Consequências
- A gold reprocessa os dias afetados por pedidos reenviados.
- Se surgir demanda de auditoria de alterações, criar `slv_vendas__pedidos_historico` (nova spec).
