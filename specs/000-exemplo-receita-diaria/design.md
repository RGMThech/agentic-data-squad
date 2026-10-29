---
id: 000
spec_versao: 1.1
versao: 1.0
status: aprovado
aprovado_por: Operador
aprovado_em: 2026-10-29
exemplo: true
---

# Design — Receita diária por loja (exemplo)

## 1. Visão geral do fluxo
```
ERP.pedidos ──► brz_vendas__pedidos ──► slv_vendas__pedidos ──► gld_vendas__receita_diaria_loja ──► M-01..M-04 / painel comercial
```

## 2. Tabelas
| Tabela | Camada | Grão | Chave | Carga | Contrato |
|--------|--------|------|-------|-------|----------|
| `brz_vendas__pedidos` | bronze | 1 linha por envio do ERP | `pedido_id`, `_ingestao_ts` | incremental append | — |
| `slv_vendas__pedidos` | silver | 1 linha por pedido (versão mais recente) | `pedido_id` | incremental merge | `contracts/slv_vendas__pedidos.yaml` |
| `gld_vendas__receita_diaria_loja` | gold | 1 linha por loja × dia | `loja_cd`, `venda_dt` | reprocessa dias afetados | `contracts/gld_vendas__receita_diaria_loja.yaml` |

## 3. Mapeamento regra → implementação
| Regra/Métrica | Tabela | Coluna(s) | Observação |
|---------------|--------|-----------|------------|
| RN-01 | gold | filtro `NOT cancelado_fl` | `cancelado_fl` calculado na silver |
| RN-02 | silver | `ROW_NUMBER()` por `pedido_id` ordenado por `_ingestao_ts DESC` | |
| RN-03 | silver | `pedido_dt = CAST(pedido_ts AS DATE)` | fuso da origem: America/Sao_Paulo |
| RN-04 | gold | `ROUND(..., 2)` só no `ticket_medio_vl` | somas mantêm `decimal(18,2)` |
| M-01..M-04 | gold | `receita_bruta_vl`, `receita_liquida_vl`, `pedidos_qt`, `ticket_medio_vl` | |

## 4. Estratégia de carga
- Incremental por: `_ingestao_ts` (bronze → silver)
- Tratamento de dado atrasado: a gold reprocessa todos os `pedido_dt` presentes no lote
- Idempotência garantida por: merge por `pedido_id` na silver e overwrite por partição na gold
- Reprocessamento histórico: carga full a partir da bronze, por mês

## 5. Dados pessoais (LGPD)
| Tabela | Coluna | Classificação | Tratamento |
|--------|--------|---------------|------------|
| `slv_vendas__pedidos` | `cliente_id` | pessoal | pseudônimo da origem; acesso restrito |
| `gld_vendas__receita_diaria_loja` | — | — | nenhuma coluna pessoal (CA-05) |

## 6. Impacto
- Tabelas/painéis existentes afetados: nenhum (feature nova)
- Quebra de contrato: não

## 7. Custo estimado
| Item | Estimativa | Premissa |
|------|------------|----------|
| Processamento por execução | baixo (minutos) | ~50 mil linhas/dia, reprocesso de 2–3 dias |
| Armazenamento/mês | < 1 GB | 24 meses de histórico |
| Frequência | 1×/dia (gold), 1×/hora (bronze/silver) | |

## 8. Decisões arquiteturais (ADRs)
- `docs/adr/0001-versao-mais-recente-do-pedido.md`

## 9. Riscos
| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| ERP reenviar pedido com `_ingestao_ts` igual | baixa | médio | desempate por `_lote_id` (tarefa futura) |
