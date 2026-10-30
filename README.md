# Agentic Data Squad

Template de repositório para operar uma **squad agêntica de Data Analytics comandada por um único humano**, usando **Spec-Driven Development (SDD)** e **Harness Engineering**.

O humano (Operador) define a intenção e aprova três gates. Nove agentes especializados executam o restante: requisitos, modelagem, ingestão, transformação, testes, BI, revisão e governança.

O template é **agnóstico de plataforma**. Funciona com Databricks, Snowflake, BigQuery, Fabric, dbt ou Spark puro. Os pontos de integração estão marcados como `# PLATAFORMA:` para você adaptar.

Os agentes podem **consultar e testar com dados reais** em Databricks, Snowflake, BigQuery ou Microsoft Fabric (e rodar dbt), com leitura só nas fontes liberadas e escrita só numa sandbox. Veja [docs/acesso-dados.md](docs/acesso-dados.md).

---

## Como funciona

```
Operador ──► pedido de negócio
                │
        [analista-requisitos] ──► spec.md ──► 🧍 G1
                │
        [arquiteto-dados] ──► design.md + contratos ──► 🧍 G2
                │
        [orquestrador] ──► tasks.md
                │
   ┌────────────┼─────────────┐
[eng-ingestao] [eng-transformacao] [analytics-bi]   ← em paralelo
   └────────────┼─────────────┘
                │
        [qa-data-quality] ──falhou──► volta ao autor (loop automático)
                │
        [revisor] ──► [governanca-docs]
                │
        Pull Request ──► 🧍 G3 ──► CI/CD ──► produção
```

---

## Estrutura

```
AGENTS.md                  # constituição da squad (fonte de verdade)
CLAUDE.md                  # ponteiro para o AGENTS.md
.claude/
  agents/                  # 9 agentes especializados (escopo + ferramentas)
  skills/                  # conhecimento reutilizável (SDD, naming, DQ, LGPD)
  settings.json            # permissões e hooks (validação automática)
templates/                 # spec, design, tasks, ADR, contrato, parecer
specs/                     # uma pasta por feature (NNN-slug)
contracts/                 # data contracts versionados
pipelines/bronze|silver|gold/<dominio>/
tests/unit|quality|golden/
semantic/                  # métricas e camada semântica
scripts/                   # validadores do harness
docs/                      # playbook do operador, gates, naming, lições
.github/workflows/         # CI que reforça os gates
```

---

## Começando

1. **Adapte a plataforma.** Busque por `PLATAFORMA:` no repositório e ajuste comandos, conexões e o MCP da sua stack em `.claude/settings.json`.
2. **Proteja a `main`.** No GitHub, exija PR, CI verde e 1 aprovação (a sua) antes do merge.
3. **Abra a primeira feature:**
   ```
   Use o agente analista-requisitos para criar a spec 001 a partir deste pedido: <descreva o problema de negócio>
   ```
4. **Siga o playbook:** [`docs/operador-humano.md`](docs/operador-humano.md).

Veja um exemplo completo em [`specs/000-exemplo-receita-diaria/`](specs/000-exemplo-receita-diaria/).

---

## Operando pelo Squad Console

Esta squad pode ser comandada pela web pelo [Squad Console](https://github.com/RGMThech/agentic-squad-console). Pelo console você:
- abre features
- aciona agentes (eles rodam no GitHub Actions)
- aprova os gates G1, G2 e G3
- acompanha custos por execução

Os papéis ficam em `.squad/members.yaml` e a configuração da squad em `.squad/squad.yaml`. Veja [`docs/console.md`](docs/console.md).

## Validadores do harness

| Script | O que garante |
|--------|---------------|
| `scripts/validate_naming.py` | Arquivos de pipeline e colunas seguem a convenção |
| `scripts/check_contracts.py` | Todo pipeline silver/gold tem contrato válido, com PII classificada |
| `scripts/check_spec.py` | Specs em implementação estão aprovadas e sem dúvidas abertas |

Todos rodam localmente, nos hooks dos agentes e no CI.

---

## Implantação recomendada

| Fase | Agentes ativos | Papel do Operador |
|------|----------------|-------------------|
| 1 — Piloto | analista-requisitos, eng-transformacao, qa-data-quality | Faz o resto e registra cada correção |
| 2 — Consolidação | + revisor, orquestrador | Correções viram regras no harness |
| 3 — Squad completa | todos os 9 | Atua só nos gates G1, G2, G3 |

**Métricas de saúde:** lead time da spec até a produção, taxa de aprovação de primeira nos gates, retrabalho por feature, custo por entrega e incidentes de qualidade em produção.
