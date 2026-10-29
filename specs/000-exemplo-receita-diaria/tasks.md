---
id: 000
spec_versao: 1.1
design_versao: 1.0
---

# Tarefas — Receita diária por loja (exemplo)

Status: `pendente` | `em_andamento` | `em_qa` | `reprovado` | `aprovado` | `bloqueado`

| ID | Tarefa | Agente | Depende de | Entradas | Saída | Critério de pronto | Ciclos QA | Status |
|----|--------|--------|------------|----------|-------|--------------------|-----------|--------|
| T-01 | Ingestão dos pedidos do ERP | eng-ingestao | — | design §2, §4 | `pipelines/bronze/vendas/brz_vendas__pedidos.py` | idempotente, colunas técnicas presentes | 1 | aprovado |
| T-02 | Silver de pedidos com dedup | eng-transformacao | T-01 | RN-02, RN-03, contrato silver | `pipelines/silver/vendas/slv_vendas__pedidos.sql` | schema = contrato, CA-02 | 2 | aprovado |
| T-03 | Gold de receita diária | eng-transformacao | T-02 | RN-01, RN-04, M-01..M-04 | `pipelines/gold/vendas/gld_vendas__receita_diaria_loja.sql` | CA-01, CA-03, CA-04, CA-05 | 1 | aprovado |
| T-04 | Métricas na camada semântica | analytics-bi | T-03 | §7 da spec | `semantic/metricas/vendas.yaml` | 1 definição por métrica | 1 | aprovado |

## Bloqueios e escalonamentos
| Data | Tarefa | Motivo | Encaminhamento |
|------|--------|--------|----------------|
| 2026-10-29 | T-02 | QA reprovou ciclo 1: data da venda usava `_ingestao_ts` | Spec atualizada para v1.1 (RN-03); lição registrada |
