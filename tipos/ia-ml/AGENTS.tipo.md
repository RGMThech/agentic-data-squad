# AGENTS.tipo.md — Squad de IA e Machine Learning

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

Squad que constrói soluções de IA — modelos preditivos, LLMs, RAG, classificadores e agentes — com avaliação objetiva contra limiares definidos antes, model card e análise de riscos de IA responsável.

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Spec** | `specs/<id>/spec.md` | `analista-requisitos` | Uso e usuários definidos, métrica de sucesso com limiar, dados disponíveis, riscos e restrições, critérios de aceite, **zero dúvidas abertas** |
| **G2 — Abordagem** | `specs/<id>/design.md` | `arquiteto-ml` | Abordagem justificada contra alternativas (inclusive regra simples), plano de avaliação com limiares, riscos de IA responsável, custos de treino e inferência |
| **G3 — Entrega** | Pull Request | `orquestrador` | Avaliação com todas as métricas no limiar (`eval.yaml`), model card completo, parecer do Revisor, tarefas encerradas, `entrega.md` |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar o trabalho, distribuir, conduzir avaliação e revisão | Treinar ou avaliar, aprovar gate |
| `analista-requisitos` | Escrever a spec com uso, métrica e riscos | Escolher técnica ou modelo |
| `arquiteto-ml` | Desenhar a abordagem e o plano de avaliação | Implementar |
| `eng-dados-ml` | Preparar dados, features, conjuntos de treino/validação/teste | Usar dado pessoal sem base legal ou sem minimização |
| `cientista-dados` | Treinar e ajustar modelos clássicos e de deep learning | Ver o conjunto de teste antes da avaliação final |
| `eng-llm` | Prompts, RAG, ferramentas e agentes com LLM | Colocar dado pessoal ou segredo em prompt |
| `avaliador` | Rodar a avaliação, registrar `eval.yaml`, reprovar | Ajustar o modelo ou o limiar |
| `mlops` | Empacotar, servir, monitorar (drift, custo, latência) | Publicar em produção |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo |
| `documentacao` | Model card, `entrega.md`, documentação de uso | Alterar modelo ou avaliação |

**Segregação de funções:** quem produz não aprova, quem verifica não corrige, quem revisa não edita.

---

## Convenções obrigatórias

- **Modelos:** `modelos/<nome>/` com `model-card.md` (template em `templates/model-card.md`); pesos e artefatos grandes ficam fora do Git (registro de modelos ou armazenamento), referenciados no card.
- **Código:** `src/`; notebooks exploratórios em `notebooks/` (o que vai para produção sai do notebook).
- **Prompts:** `prompts/<nome>.md`, versionados, com variáveis explícitas (`{{pergunta}}`).
- **Avaliações:** `avaliacoes/<NNN>-<slug>/eval.yaml` (template em `templates/eval.yaml`), com métricas, limiares e resultado. O validador confere se o resultado declarado bate com os números.
- **Conjuntos de dados:** treino, validação e teste separados; o teste é usado uma vez, na avaliação final.
- **Reprodutibilidade:** semente, versão dos dados e do código registradas no `eval.yaml`.

---

## Segurança, LGPD e reputação

- Limiares de avaliação definidos no G2, **antes** de treinar; o avaliador não ajusta limiar.
- Dados pessoais: minimização, base legal registrada na spec e nada de registro identificável em prompts, avaliações ou notebooks. O validador procura CPF, e-mail e telefone em `prompts/` e `avaliacoes/`.
- Riscos de IA responsável avaliados no design: vieses e métricas por grupo, alucinação, injeção de prompt, uso indevido, explicabilidade.
- Decisão automatizada que afete pessoas: prever revisão humana (LGPD art. 20).
- Nenhum modelo é publicado pelos agentes: o deploy é do Operador, depois do G3.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] `python scripts/gates.py` passando
- [ ] Avaliação com todas as métricas no limiar, inclusive por grupo quando houver risco de viés (`check_ia.py`)
- [ ] Model card completo
- [ ] Monitoramento (drift, qualidade, custo) definido
- [ ] Parecer do Revisor sem bloqueios
- [ ] `specs/<feature>/entrega.md` lista tudo o que foi entregue e onde está
