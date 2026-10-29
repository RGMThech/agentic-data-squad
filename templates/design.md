---
id: NNN
spec_versao: 1.0
versao: 1.0
status: rascunho        # rascunho | em_revisao | aprovado  (aprovado: só o Operador)
aprovado_por:
aprovado_em:
---

# Design — <título>

## 1. Visão geral do fluxo
```
<fonte> ──► brz_<dom>__<ent> ──► slv_<dom>__<ent> ──► gld_<dom>__<ent> ──► métricas / painel
```

## 2. Tabelas
| Tabela | Camada | Grão | Chave | Carga | Contrato |
|--------|--------|------|-------|-------|----------|
|        |        |      |       | incremental / full | `contracts/<tabela>.yaml` |

## 3. Mapeamento regra → implementação
| Regra/Métrica | Tabela | Coluna(s) | Observação |
|---------------|--------|-----------|------------|
| RN-01 |  |  |  |

## 4. Estratégia de carga
- Incremental por: <coluna de watermark>
- Tratamento de dado atrasado:
- Idempotência garantida por:
- Reprocessamento histórico:

## 5. Dados pessoais (LGPD)
| Tabela | Coluna | Classificação | Tratamento |
|--------|--------|---------------|------------|
|        |        |               |            |

## 6. Impacto
- Tabelas/painéis existentes afetados:
- Quebra de contrato: sim/não — plano:

## 7. Custo estimado
| Item | Estimativa | Premissa |
|------|------------|----------|
| Processamento por execução |  |  |
| Armazenamento/mês |  |  |
| Frequência |  |  |

## 8. Decisões arquiteturais (ADRs)
- `docs/adr/NNNN-<slug>.md`

## 9. Riscos
| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
|       |               |         |           |
