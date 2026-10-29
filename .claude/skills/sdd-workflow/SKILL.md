---
name: sdd-workflow
description: Fluxo Spec-Driven Development da squad — como uma feature vai do pedido à produção, quem faz cada etapa e quais gates humanos existem. Use ao iniciar qualquer feature, ao decidir o próximo passo ou ao detectar mudança de escopo.
---

# Fluxo SDD da squad

## Etapas

| # | Etapa | Agente | Artefato | Saída para |
|---|-------|--------|----------|------------|
| 1 | Pedido | Operador | mensagem | analista-requisitos |
| 2 | Especificação | analista-requisitos | `specs/<id>/spec.md` | **G1** |
| 3 | Design | arquiteto-dados | `design.md`, `contracts/*.yaml`, ADRs | **G2** |
| 4 | Planejamento | orquestrador | `tasks.md` | agentes executores |
| 5 | Implementação | eng-ingestao, eng-transformacao, analytics-bi | `pipelines/**`, `semantic/**` | qa |
| 6 | Qualidade | qa-data-quality | `qa-report.md` | autor (se falhar) ou revisor |
| 7 | Revisão | revisor | `review.md` | governanca-docs |
| 8 | Documentação | governanca-docs | `docs/**` | orquestrador |
| 9 | Pull Request | orquestrador | PR | **G3** |
| 10 | Deploy | CI/CD | — | produção |

## Cabeçalho de status (spec e design)

```yaml
---
id: 001
titulo: Receita diária por loja
versao: 1.0
status: rascunho   # rascunho | em_revisao | aprovado
aprovado_por:      # preenchido só pelo Operador
aprovado_em:
---
```

## Como identificar o próximo passo

1. Não existe `spec.md` → etapa 2.
2. Spec não aprovada → aguardar Operador (G1).
3. Spec aprovada, sem `design.md` aprovado → etapa 3 ou aguardar G2.
4. Sem `tasks.md` → etapa 4.
5. Tarefas abertas → etapa 5/6.
6. Tudo aprovado no QA, sem `review.md` → etapa 7.
7. Sem PR → etapas 8 e 9.

## Mudança de escopo

Sinal: alguém precisa implementar algo que não está na spec, ou a spec contradiz o dado real.
Ação: parar a tarefa, registrar no `tasks.md`, devolver ao analista-requisitos, que incrementa `versao` e volta ao G1. Nunca "resolver no código".

## Mensagem ao Operador (formato padrão)

```
🧍 Decisão necessária — <gate ou tema>
Feature: <id> <título>
O que preciso: <1 frase>
Opções: A) ... B) ...
Recomendação: <opção e motivo em 1 linha>
Artefato: <caminho>
```
