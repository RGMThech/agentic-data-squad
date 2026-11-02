---
name: sdd-workflow
description: Fluxo Spec-Driven Development da squad (qualquer tipo) — como uma feature vai do pedido à entrega, quem faz cada etapa e quais gates humanos existem. Use ao iniciar qualquer feature, ao decidir o próximo passo ou ao detectar mudança de escopo.
---

# Fluxo SDD da squad

## Etapas

Os agentes de cada papel estão em `.squad/tipo.yaml` (papeis) e em `AGENTS.tipo.md`.

| # | Etapa | Papel | Artefato | Saída para |
|---|-------|-------|----------|------------|
| 1 | Pedido | Operador | `specs/<id>/pedido.md` (console) | especificação |
| 2 | Especificação | `papeis.especificacao` | `specs/<id>/spec.md` | **G1** |
| 3 | Design / plano | `papeis.design` | `specs/<id>/design.md` (+ ADRs e artefatos do tipo) | **G2** |
| 4 | Planejamento | `papeis.orquestracao` | `specs/<id>/tasks.md` | executores |
| 5 | Execução | executores do tipo | artefatos do tipo | QA |
| 6 | Qualidade | QA do tipo | `qa-report.md` | autor (se falhar) ou revisor |
| 7 | Revisão | `revisor` | `review.md` | documentação |
| 8 | Documentação | `papeis.documentacao` | `entrega.md`, `docs/**` | orquestração |
| 9 | Pull Request | `papeis.orquestracao` | PR | **G3** |
| 10 | Publicação | CI/CD ou Operador | — | produção / canais |

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

## Ciclo de vida das tarefas e reabertura

- **Encerrada** = `aprovado`, `nao_executar` ou `resolvido_fora`. O G3 (CI e console) só libera com todas encerradas.
- `nao_executar` e `resolvido_fora` são decisões do Operador, com justificativa em "Decisões sobre tarefas"; a governança leva isso para o `entrega.md`.
- O Operador pode pedir para **reexecutar** uma tarefa: ela volta a `pendente` com a orientação dele.
- Uma feature entregue pode ser **reaberta** (ajustes, tarefas pendentes ou mudança de especificação): nova rodada na mesma branch `squad/<id>`, com PR novo. Registre a rodada em "Reaberturas" e crie tarefas novas com o próximo `T-xx`.
- Se a reabertura mudar a spec, ela volta ao G1 (e o design ao G2) antes de qualquer tarefa nova.

## Mensagem ao Operador (formato padrão)

```
🧍 Decisão necessária — <gate ou tema>
Feature: <id> <título>
O que preciso: <1 frase>
Opções: A) ... B) ...
Recomendação: <opção e motivo em 1 linha>
Artefato: <caminho>
```
