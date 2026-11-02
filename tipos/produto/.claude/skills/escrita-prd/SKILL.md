---
name: escrita-prd
description: Como escrever PRD, histórias de usuário (INVEST), critérios de aceite e priorizar com RICE. Use ao escrever ou revisar PRD e backlog.
---

# Escrita de PRD

## Estrutura (validada por `scripts/check_produto.py`)
Problema e contexto · Objetivos e métricas · Escopo · Fora de escopo · Histórias de usuário · Requisitos · Riscos e dependências · Plano de lançamento.

## Histórias (INVEST)
`Como <persona>, quero <ação>, para <benefício>` — Independente, Negociável, Valiosa, Estimável, Pequena (cabe numa sprint), Testável.
Cada história tem critérios **Dado / Quando / Então**, incluindo erro e limite.

## RICE
| Fator | Escala |
|-------|--------|
| Alcance | pessoas ou eventos por trimestre |
| Impacto | 3 enorme · 2 alto · 1 médio · 0,5 baixo · 0,25 mínimo |
| Confiança | 0 a 1 (1 = dados sólidos; 0,5 = palpite informado) |
| Esforço | pessoas-semana |

Nota = alcance × impacto × confiança ÷ esforço. O backlog (`backlog/<NNN>-<slug>.yaml`) fica em ordem decrescente de nota, salvo decisão do Operador registrada.
