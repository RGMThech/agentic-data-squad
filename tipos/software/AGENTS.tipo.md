# AGENTS.tipo.md — Squad de Desenvolvimento de Software

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

Squad que entrega funcionalidades, APIs, integrações e correções de software: da história de usuário ao código testado, revisado e pronto para release.

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Spec** | `specs/<id>/spec.md` | `analista-requisitos` | Histórias no formato *Como…, quero…, para…*, regras de negócio, requisitos não funcionais, critérios de aceite testáveis, **zero dúvidas abertas** |
| **G2 — Arquitetura** | `specs/<id>/design.md` + ADRs | `arquiteto-software` | Solução coerente com a arquitetura atual, contratos de interface definidos, segurança e estratégia de testes cobertas, plano de rollback |
| **G3 — Release** | Pull Request | `orquestrador` | CI verde, cobertura dos critérios de aceite, parecer do Revisor sem bloqueios, tarefas encerradas, `entrega.md` |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar o trabalho, distribuir, conduzir QA e revisão | Escrever código, aprovar gate |
| `analista-requisitos` | Escrever histórias, regras e critérios de aceite | Decidir regra de negócio sozinho |
| `arquiteto-software` | Desenhar a solução, contratos de API, ADRs | Implementar |
| `dev-backend` | Código de servidor, APIs, integrações, migrações | Mudar contratos aprovados sem voltar ao arquiteto |
| `dev-frontend` | Interface, acessibilidade, integração com a API | Mudar contratos de API |
| `devops` | CI/CD, infraestrutura como código, observabilidade | Publicar em produção |
| `qa-software` | Escrever e rodar testes, reprovar entregas | Corrigir o código que testa |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo |
| `documentacao` | README, docs, changelog, `entrega.md` | Alterar código |

**Segregação de funções:** quem produz não aprova, quem verifica não corrige, quem revisa não edita.

---

## Convenções obrigatórias

- **Código:** em `src/` (serviços, bibliotecas) ou `app/` (aplicação web/mobile); infraestrutura em `infra/`.
- **Testes:** em `tests/`, espelhando a estrutura do código; cada critério de aceite tem pelo menos um teste com o ID (`CA-01`) no nome ou na docstring.
- **Histórias de usuário:** `Como <persona>, quero <ação>, para <benefício>`, cada uma com critérios de aceite Dado/Quando/Então.
- **Decisões de arquitetura:** ADR em `docs/adr/NNNN-<slug>.md` (template em `templates/adr.md`).
- **Commits:** `tipo(escopo): descrição` (Conventional Commits: feat, fix, refactor, test, docs, chore).
- **Branches:** `squad/<NNN>-<slug>` (o console cria).
- Siga a stack, o estilo e as bibliotecas já usados no repositório (`docs/arquitetura.md`); dependência nova só com justificativa no design.

---

## Segurança, LGPD e reputação

- Nunca coloque segredo, token, senha ou chave no código, nos testes ou nos documentos: use variáveis de ambiente. `scripts/check_software.py` bloqueia padrões conhecidos.
- Dados pessoais em testes só sintéticos (nada copiado de produção).
- Toda entrada externa é validada; consultas a banco sempre parametrizadas (skill `seguranca-app`).
- Dependências novas: versão fixada e sem vulnerabilidade conhecida.
- Nada vai para produção sem o G3: os agentes não fazem deploy.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] `python scripts/gates.py` passando
- [ ] Testes automatizados cobrindo todos os critérios de aceite, passando no CI
- [ ] Sem segredos no código (`check_software.py`)
- [ ] Migrações de dados com caminho de volta (rollback) descrito
- [ ] README / docs e changelog atualizados
- [ ] Parecer do Revisor sem bloqueios
- [ ] `specs/<feature>/entrega.md` lista tudo o que foi entregue e onde está
