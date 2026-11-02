# Agentic Squad

Template de repositório para operar uma **squad agêntica comandada por um único humano**, usando **Spec-Driven Development (SDD)** e **Harness Engineering**.

O humano (Operador) define a intenção e aprova três gates. Agentes especializados fazem o restante: especificação, desenho da solução, execução em paralelo, verificação, revisão e documentação. O trabalho é organizado **por feature** (um pedido de negócio) e **por tarefa** (uma atividade com um único agente dono).

---

## Tipos de squad

O mesmo modelo de atuação serve para áreas diferentes. Cada tipo traz seus próprios agentes, skills, templates e validadores:

| Tipo | Para quê | G1 · G2 · G3 | Agentes executores |
|------|----------|--------------|--------------------|
| **Data Analytics** (`dados`) | Pipelines, modelos de dados, métricas e painéis | Spec · Design · Produção | ingestão, transformação, BI, QA de dados |
| **Desenvolvimento de Software** (`software`) | Funcionalidades, APIs, integrações e correções | Spec · Arquitetura · Release | backend, frontend, DevOps, QA |
| **Marketing** (`marketing`) | Campanhas, conteúdo, SEO e mídia | Briefing · Plano · Publicação | redator, designer, SEO, mídia, revisor de marca |
| **Produto** (`produto`) | Discovery, PRD, protótipos e backlog priorizado | Problema · PRD · Handoff | pesquisa UX, design UX, dados de produto, QA |
| **IA e Machine Learning** (`ia-ml`) | Modelos, LLMs, RAG e agentes | Spec · Abordagem · Entrega | dados para ML, cientista, LLM, MLOps, avaliador |
| **Vendas e pré-vendas** (`vendas`) | Pesquisa de contas, cadências, propostas, playbooks | Objetivo · Playbook · Liberação | pesquisa de contas, redator, propostas, apresentações |
| **Atendimento / CX** (`atendimento`) | Base de conhecimento, fluxos e chatbot, macros | Spec · Jornada · Publicação | análise de tickets, redator de KB, fluxos, QA de CX |

A raiz deste repositório é o tipo **Data Analytics**. Os outros tipos ficam em `tipos/<tipo>/`, com a mesma estrutura de pastas. O catálogo está em [`tipos/base.yaml`](tipos/base.yaml).

Ao criar uma squad pelo **Squad Console**, você escolhe o tipo e o console monta o repositório com o pacote certo. Para fazer isso à mão:

```bash
python scripts/instanciar_tipo.py marketing   # aplica o tipo e remove a pasta tipos/
```

---

## Como funciona

```
Operador ──► pedido (specs/<NNN>/pedido.md)
                │
     [agente de especificação] ──► spec.md ──► 🧍 G1
                │
     [agente de design] ──► design.md ──► 🧍 G2
                │
        [orquestrador] ──► tasks.md
                │
   ┌────────────┼─────────────┐
[executor]  [executor]  [executor]     ← em paralelo
   └────────────┼─────────────┘
                │
          [QA do tipo] ──reprovou──► volta ao autor (loop automático)
                │
        [revisor] ──► [documentação] ──► entrega.md
                │
        Pull Request ──► 🧍 G3
```

Os nomes de cada papel, dos gates e dos validadores do tipo estão em `.squad/tipo.yaml`.

---

## Estrutura

```
AGENTS.md                  # constituição comum a todas as squads
AGENTS.tipo.md             # papéis, convenções e definição de pronto do tipo
CLAUDE.md                  # ponteiro para os dois acima
.squad/
  squad.yaml               # configuração da squad (modelo, limites, acesso a dados)
  tipo.yaml                # tipo: rótulos dos gates, papéis, seções da spec, validadores
  members.yaml             # pessoas e papéis no console
.claude/
  agents/                  # agentes do tipo (escopo + ferramentas)
  skills/                  # conhecimento reutilizável (SDD, LGPD, acesso a dados e skills do tipo)
  settings.json            # permissões e hooks (validação automática)
templates/                 # spec, design, tasks, QA, parecer, entrega e templates do tipo
specs/                     # uma pasta por feature (NNN-slug)
scripts/                   # validadores do harness (gates.py roda todos os do tipo)
docs/                      # playbook do operador, console, acesso a dados, lições
tipos/                     # pacotes dos outros tipos (só no template)
.github/workflows/         # agentes no GitHub Actions e CI que reforça os gates
```

---

## Começando

1. **Crie a squad pelo Squad Console** (recomendado) ou use este template e rode `python scripts/instanciar_tipo.py <tipo>`.
2. **Proteja a `main`.** No GitHub, exija PR, CI verde e 1 aprovação (a sua) antes do merge.
3. **Preencha o contexto do tipo:** por exemplo `docs/arquitetura.md` (software), `docs/marca.md` (marketing), `docs/oferta.md` (vendas), `docs/politicas.md` (atendimento), `docs/produto.md` (produto).
4. **Abra a primeira feature** pelo console, ou no Claude Code:
   ```
   Use o agente de especificação para criar a spec 001 a partir deste pedido: <descreva o pedido>
   ```
5. **Siga o playbook:** [`docs/operador-humano.md`](docs/operador-humano.md).

No tipo Data Analytics há um exemplo completo em [`specs/000-exemplo-receita-diaria/`](specs/000-exemplo-receita-diaria/).

---

## Operando pelo Squad Console

Esta squad pode ser comandada pela web pelo [Squad Console](https://github.com/RGMThech/agentic-squad-console). Pelo console você:
- cria squads de qualquer tipo, em uma ou várias organizações do GitHub
- abre features, responde dúvidas e edita a spec
- aciona agentes (eles rodam no GitHub Actions)
- aprova os gates G1, G2 e G3, decide sobre tarefas e reabre features
- baixa tudo o que foi entregue (PDF, DOCX, TXT ou .zip)
- acompanha custos por execução

Os papéis ficam em `.squad/members.yaml` e a configuração em `.squad/squad.yaml`. Veja [`docs/console.md`](docs/console.md).

## Validadores do harness

`python scripts/gates.py` roda todos os validadores declarados em `.squad/tipo.yaml`. Em todos os tipos:

| Script | O que garante |
|--------|---------------|
| `scripts/check_spec.py` | Spec e design com status válido, G1 sem dúvidas abertas, G3 só com tarefas encerradas |
| `scripts/check_tipo.py` | A squad está coerente com o tipo (papéis, agentes, templates, validadores) |
| `scripts/proteger_harness.py` | Agentes não alteram as próprias regras |

E um validador por tipo: `validate_naming.py` e `check_contracts.py` (dados), `check_software.py`, `check_marketing.py`, `check_produto.py`, `check_ia.py`, `check_vendas.py`, `check_atendimento.py`.

Todos rodam localmente, nos hooks dos agentes e no CI. No template, o CI também instancia cada tipo e roda os validadores e testes dele (`scripts/testar_tipos.py`).

---

## Implantação recomendada

| Fase | Agentes ativos | Papel do Operador |
|------|----------------|-------------------|
| 1 — Piloto | especificação, um executor, QA | Faz o resto e registra cada correção |
| 2 — Consolidação | + revisor, orquestrador | Correções viram regras no harness |
| 3 — Squad completa | todos | Atua só nos gates G1, G2, G3 |

**Métricas de saúde:** lead time do pedido até a entrega, taxa de aprovação de primeira nos gates, retrabalho por feature, custo por entrega e incidentes depois da entrega.
