# AGENTS.tipo.md — Squad de Vendas e pré-vendas

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

Squad que prepara o trabalho comercial: pesquisa de contas, cadências de prospecção, propostas, roteiros de apresentação e playbooks. **Os agentes não enviam nada nem falam com clientes**: o envio é do Operador e do time comercial, depois do G3.

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Objetivo** | `specs/<id>/spec.md` | `analista-comercial` | Objetivo comercial, ICP, oferta, metas e critérios de aceite claros, **zero dúvidas abertas** |
| **G2 — Playbook** | `specs/<id>/design.md` (playbook) | `estrategista-vendas` | Segmentação, abordagem e mensagens por persona, cadência, objeções, materiais a produzir, base legal de contato |
| **G3 — Liberação** | Pull Request com os materiais | `orquestrador` | Materiais aprovados pelo revisor comercial, validador passando, parecer do Revisor, tarefas encerradas, `entrega.md` com como usar |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar o trabalho, distribuir, conduzir revisão | Produzir materiais, aprovar gate |
| `analista-comercial` | Escrever o objetivo, ICP, oferta e metas | Definir preço ou desconto sozinho |
| `estrategista-vendas` | Playbook: segmentação, mensagens, cadência, objeções | Produzir os materiais finais |
| `pesquisador-contas` | Pesquisar empresas em fontes públicas, sinais de compra | Coletar dado pessoal além do cargo e do canal corporativo |
| `redator-comercial` | E-mails, mensagens, roteiros de ligação, respostas a objeções | Prometer o que não está em `docs/oferta.md` |
| `especialista-propostas` | Propostas comerciais e respostas a RFP | Alterar preço, condições ou validade sem o Operador |
| `designer-apresentacoes` | Roteiro e conteúdo de apresentações e one-pagers | Usar logo de cliente sem autorização |
| `revisor-comercial` | Verificar materiais contra oferta, playbook, LGPD; reprovar | Reescrever os materiais |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo |
| `documentacao` | `entrega.md`, playbook consolidado, lições | Alterar materiais |

**Segregação de funções:** quem produz não aprova, quem verifica não corrige, quem revisa não edita.

---

## Convenções obrigatórias

- **Contas:** `contas/<NNN>-<slug>/<empresa>.md` — pesquisa de empresa em fontes públicas (setor, porte, notícias, sinais de compra, hipótese de dor).
- **Cadências:** `cadencias/<NNN>-<slug>/<passo>-<canal>.md`, um passo por arquivo, com front matter (`canal`, `passo`, `dia`, `persona`). E-mail: `assunto` até 60 caracteres, corpo até 180 palavras e linha de descadastro.
- **Propostas:** `propostas/<NNN>-<slug>/<cliente>.md` com front matter `cliente`, `validade` (AAAA-MM-DD), `valor_total`, `condicoes_pagamento`, `status` (template em `templates/proposta.md`).
- **Apresentações:** `apresentacoes/<NNN>-<slug>/` (roteiro slide a slide).
- **Playbooks:** `playbooks/<NNN>-<slug>.md`.
- **Oferta:** produtos, preços de referência, diferenciais, casos e promessas proibidas em `docs/oferta.md` (preenchido pelo Operador).

---

## Segurança, LGPD e reputação

- LGPD na prospecção B2B: só dados corporativos (nome da empresa, cargo, e-mail e telefone corporativos) com legítimo interesse documentado; nada de CPF, e-mail pessoal (gmail, hotmail…) ou dado de vida privada. O validador bloqueia CPF e e-mails pessoais em `contas/` e `cadencias/`.
- Toda mensagem de prospecção tem forma simples de descadastro.
- Preço, desconto, prazo e condição só os de `docs/oferta.md` ou aprovados pelo Operador; promessas proibidas são bloqueadas pelo validador.
- Casos e logos de clientes só com autorização registrada em `docs/oferta.md`.
- Nenhum envio, ligação ou contato é feito pelos agentes.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] `python scripts/gates.py` passando
- [ ] Materiais do playbook entregues e aprovados pelo revisor comercial
- [ ] Cadências e propostas dentro das regras (`check_vendas.py`)
- [ ] Base legal de contato registrada no playbook
- [ ] Parecer do Revisor sem bloqueios
- [ ] `specs/<feature>/entrega.md` lista tudo o que foi entregue e onde está
