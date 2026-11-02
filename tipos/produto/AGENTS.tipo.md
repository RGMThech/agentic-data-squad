# AGENTS.tipo.md — Squad de Produto

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

Squad de discovery e definição de produto: entende o problema com evidências, escreve o PRD, prototipa e entrega um backlog priorizado e pronto para o time de desenvolvimento (ou para uma squad de software).

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Problema** | `specs/<id>/spec.md` (definição do problema) | `analista-produto` | Problema claro, evidências citadas, público definido, resultado esperado mensurável, **zero dúvidas abertas** |
| **G2 — PRD** | `specs/<id>/design.md` (PRD) | `product-manager` | Objetivos e métricas, escopo e fora de escopo, histórias de usuário, requisitos, riscos e plano de lançamento |
| **G3 — Handoff** | Pull Request com pesquisa, protótipos e backlog | `orquestrador` | Backlog priorizado (RICE) e pronto para desenvolvimento, protótipos validados, parecer do Revisor, tarefas encerradas, `entrega.md` |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar o trabalho, distribuir, conduzir revisão | Decidir prioridade, aprovar gate |
| `analista-produto` | Definir o problema, reunir evidências, dúvidas | Propor solução antes do G1 |
| `product-manager` | Escrever o PRD, priorizar, definir métricas | Fechar escopo sem o Operador |
| `pesquisador-ux` | Roteiros de entrevista, sínteses, jornadas, personas | Guardar dado pessoal de participante |
| `designer-ux` | Fluxos, wireframes e protótipos navegáveis (HTML) | Mudar o escopo do PRD |
| `analista-dados-produto` | Dimensionar oportunidade, métricas, plano de experimento | Ler dados pessoais não mascarados |
| `qa-produto` | Verificar PRD, histórias, critérios e protótipos; reprovar | Reescrever o que verifica |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo |
| `documentacao` | `entrega.md`, docs de produto, roadmap | Alterar PRD ou backlog |

**Segregação de funções:** quem produz não aprova, quem verifica não corrige, quem revisa não edita.

---

## Convenções obrigatórias

- **Pesquisa:** `pesquisa/<NNN>-<slug>/` (roteiros, sínteses anonimizadas, jornadas, personas).
- **Protótipos:** `prototipos/<NNN>-<slug>/` (HTML navegável ou especificação de telas).
- **Backlog:** `backlog/<NNN>-<slug>.yaml`, um item por história, com RICE (o validador recalcula a nota). Formato em `templates/backlog.yaml`.
- **Histórias:** `Como <persona>, quero <ação>, para <benefício>`, com critérios de aceite Dado/Quando/Então.
- **Priorização:** RICE = alcance × impacto × confiança ÷ esforço. Impacto em {0,25; 0,5; 1; 2; 3}, confiança de 0 a 1, esforço em pessoas-semana.

---

## Segurança, LGPD e reputação

- Participantes de pesquisa são anonimizados (P1, P2…): nada de nome, e-mail, telefone ou CPF no repositório. O validador procura esses dados em `pesquisa/`.
- Gravações e transcrições originais ficam fora do repositório, com consentimento do participante.
- Números de mercado e de uso sempre com fonte; estimativa é marcada como estimativa.
- Os agentes não falam com clientes nem publicam pesquisas: preparam roteiros e materiais para o Operador.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] `python scripts/gates.py` passando
- [ ] PRD completo, com histórias e critérios de aceite (`check_produto.py`)
- [ ] Backlog com RICE consistente e itens prontos para desenvolvimento
- [ ] Pesquisa anonimizada (sem dados pessoais)
- [ ] Parecer do Revisor sem bloqueios
- [ ] `specs/<feature>/entrega.md` lista tudo o que foi entregue e onde está
