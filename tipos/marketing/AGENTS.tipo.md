# AGENTS.tipo.md — Squad de Marketing

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

Squad que planeja e produz campanhas e conteúdo: do briefing ao plano de campanha, às peças por canal revisadas contra a marca e ao relatório de resultados. **Os agentes não publicam nada**: a publicação é do Operador, depois do G3.

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Briefing** | `specs/<id>/spec.md` | `estrategista` | Objetivo, público, mensagem, KPIs com meta, canais, restrições e critérios de aceite claros, **zero dúvidas abertas** |
| **G2 — Plano** | `specs/<id>/design.md` (plano de campanha) | `planejador-campanha` | Conceito criativo, lista de peças por canal, calendário, mídia e orçamento, mensuração com UTMs |
| **G3 — Publicação** | Pull Request com as peças | `orquestrador` | Peças aprovadas pelo revisor de marca, validador passando, parecer do Revisor, tarefas encerradas, `entrega.md` com o que publicar, onde e quando |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar em peças/tarefas, distribuir, conduzir revisão | Produzir peças, aprovar gate |
| `estrategista` | Escrever o briefing, KPIs e dúvidas | Decidir orçamento ou promessa comercial sozinho |
| `planejador-campanha` | Conceito, plano de peças, calendário, plano de mídia | Produzir as peças finais |
| `redator` | Textos das peças, roteiros, e-mails, artigos | Inventar dado, depoimento ou promessa |
| `designer-conteudo` | Especificação de arte, roteiro visual, prompts de imagem | Usar imagem, marca ou pessoa real sem licença |
| `especialista-seo` | Palavras-chave, títulos, meta descrições, estrutura | Mudar a mensagem aprovada |
| `analista-midia` | Segmentação, distribuição de verba, UTMs | Ativar campanha ou gastar verba |
| `revisor-marca` | Verificar peças contra marca, briefing e legislação; reprovar | Reescrever as peças |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo |
| `analista-performance` | Plano de mensuração, relatório de resultados, `entrega.md` | Alterar peças |

**Segregação de funções:** quem produz não aprova, quem verifica não corrige, quem revisa não edita.

---

## Convenções obrigatórias

- **Peças:** `pecas/<NNN>-<slug>/<canal>-<nome>.md`, uma peça por arquivo, com front matter (`canal`, `formato`, `objetivo`, `publico`, `cta`, `status`). O validador confere campos, limites de caracteres por canal e UTMs.
- **Canais aceitos:** `linkedin`, `instagram`, `facebook`, `x`, `tiktok`, `youtube`, `email`, `blog`, `landing-page`, `google-ads`, `meta-ads`, `whatsapp`.
- **Links:** todo `url` de peça leva `utm_source`, `utm_medium` e `utm_campaign` (padrão: `utm_campaign=<NNN>-<slug>`).
- **Planos de campanha e mídia:** `campanhas/<NNN>-<slug>/`.
- **Relatórios de resultado:** `relatorios/<NNN>-<slug>.md`.
- **Marca:** voz, tom, termos e promessas proibidas em `docs/marca.md`. O validador bloqueia os termos proibidos.

---

## Segurança, LGPD e reputação

- Nunca publicar, agendar, impulsionar ou enviar nada: só o Operador, depois do G3.
- Sem depoimento, número, prêmio ou estudo inventado: toda afirmação de resultado tem fonte citada na peça (comentário `<!-- fonte: … -->`).
- Publicidade segue o Código do CONAR e o CDC: comparações e superlativos só com comprovação; publicidade identificada como tal.
- LGPD: listas de e-mail e públicos só com base legal (consentimento ou legítimo interesse documentado); nunca colocar dados de clientes nas peças ou no repositório.
- Imagens, músicas, marcas e pessoas reais só com licença ou autorização registrada na peça.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] `python scripts/gates.py` passando
- [ ] Todas as peças do plano entregues, com `status: aprovado` pelo revisor de marca
- [ ] Peças dentro dos limites do canal e com UTMs (`check_marketing.py`)
- [ ] Plano de mensuração com KPIs e metas do briefing
- [ ] Parecer do Revisor sem bloqueios
- [ ] `specs/<feature>/entrega.md` lista tudo o que foi entregue e onde está
