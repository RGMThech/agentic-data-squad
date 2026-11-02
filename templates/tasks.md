---
id: NNN
spec_versao: 1.0
design_versao: 1.0
---

# Tarefas — <título>

Status: `pendente` | `em_andamento` | `em_qa` | `reprovado` | `bloqueado` | `aprovado` | `nao_executar` | `resolvido_fora`

- Use só a palavra do status na coluna; observação vai depois de " — " (ex.: `aprovado — QA ok na 2ª rodada`).
- `nao_executar` e `resolvido_fora` são decisões do **Operador** e exigem justificativa; ficam em "Decisões sobre tarefas".
- O G3 só libera com todas as tarefas em `aprovado`, `nao_executar` ou `resolvido_fora`.

| ID | Tarefa | Agente | Depende de | Entradas | Saída | Critério de pronto | Ciclos QA | Status |
|----|--------|--------|------------|----------|-------|--------------------|-----------|--------|
| T-01 |  | <agente> | — |  |  |  | 0 | pendente |
| T-02 |  | <agente> | T-01 |  |  |  | 0 | pendente |

## Bloqueios e escalonamentos
| Data | Tarefa | Motivo | Encaminhamento |
|------|--------|--------|----------------|
|      |        |        |                |

## Decisões sobre tarefas
| Data | Tarefa | Decisão | Justificativa | Quem |
|------|--------|---------|---------------|------|

## Reaberturas
| Data | Quem | Tipo | O que fazer |
|------|------|------|-------------|
