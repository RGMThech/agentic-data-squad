# AGENTS.tipo.md — Squad de Atendimento / CX

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

Squad que melhora o atendimento: analisa motivos de contato, escreve a base de conhecimento, desenha fluxos de atendimento e de chatbot e cria macros, sempre com saída para um humano. **Os agentes não publicam nem respondem clientes**: a publicação é do Operador, depois do G3.

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Spec** | `specs/<id>/spec.md` | `analista-cx` | Problema, motivos de contato com volume, canais, indicadores (SLA, CSAT, FCR) com meta e critérios de aceite, **zero dúvidas abertas** |
| **G2 — Jornada** | `specs/<id>/design.md` (jornada) | `arquiteto-cx` | Jornada atual e desejada, artigos, fluxos e macros a produzir, regras de escalonamento para humano, tom de voz |
| **G3 — Publicação** | Pull Request com artigos, fluxos e macros | `orquestrador` | Conteúdos aprovados pelo QA de CX, fluxos válidos (com saída para humano), parecer do Revisor, tarefas encerradas, `entrega.md` com o que publicar e onde |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar o trabalho, distribuir, conduzir QA e revisão | Produzir conteúdo, aprovar gate |
| `analista-cx` | Escrever a spec, motivos de contato, indicadores | Decidir política (reembolso, prazo) sozinho |
| `arquiteto-cx` | Desenhar a jornada, escalonamento, conteúdos a produzir | Escrever os conteúdos finais |
| `analista-tickets` | Classificar motivos, volumes e causas a partir de tickets anonimizados | Copiar ticket com dado do cliente |
| `redator-kb` | Artigos da base de conhecimento e macros | Criar política que não está em `docs/politicas.md` |
| `designer-fluxos` | Fluxos de atendimento e chatbot (YAML) | Criar fluxo sem saída para humano |
| `qa-cx` | Testar fluxos e conteúdos contra a spec e as políticas; reprovar | Reescrever o que testa |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo |
| `documentacao` | `entrega.md`, catálogo da base e dos fluxos | Alterar conteúdo |

**Segregação de funções:** quem produz não aprova, quem verifica não corrige, quem revisa não edita.

---

## Convenções obrigatórias

- **Base de conhecimento:** `kb/<categoria>/<slug>.md`, um artigo por arquivo, com front matter (`titulo`, `categoria`, `publico` cliente|interno, `status`, `revisado_em` AAAA-MM-DD). Template em `templates/artigo-kb.md`.
- **Fluxos e chatbot:** `fluxos/<slug>.yaml` com `inicio` e `nos` (tipos `mensagem`, `pergunta`, `acao`, `humano`, `fim`). O validador exige: nó inicial existente, referências válidas, todos os nós alcançáveis, saída para `humano` alcançável, nenhum beco sem saída e mensagens de até 640 caracteres. Template em `templates/fluxo.yaml`.
- **Macros:** `macros/<slug>.md` com front matter (`titulo`, `motivo`, `canal`, `status`).
- **Análises de tickets:** `analises/<NNN>-<slug>.md` (somente números agregados e exemplos anonimizados).
- **Políticas e tom:** `docs/politicas.md` (preenchido pelo Operador): prazos, reembolso, trocas, SLA, tom de voz, quando escalar.

---

## Segurança, LGPD e reputação

- Nada de dado de cliente (nome, CPF, e-mail, telefone, endereço, número de pedido real) em artigos, fluxos, macros ou análises. O validador procura CPF, e-mail e telefone.
- Todo fluxo automatizado oferece saída para um atendente humano.
- Políticas (prazos, valores, reembolso) só as de `docs/politicas.md`; conteúdo que contradiz política é reprovado.
- Atendimento segue o CDC e o Decreto do SAC (Decreto 11.034/2022): acesso a humano, informação clara, registro do atendimento.
- Nenhum conteúdo é publicado e nenhum cliente é respondido pelos agentes.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] `python scripts/gates.py` passando
- [ ] Artigos, fluxos e macros previstos na jornada entregues e aprovados pelo QA de CX
- [ ] Fluxos válidos e com saída para humano (`check_atendimento.py`)
- [ ] Indicadores e forma de medir definidos
- [ ] Parecer do Revisor sem bloqueios
- [ ] `specs/<feature>/entrega.md` lista tudo o que foi entregue e onde está
