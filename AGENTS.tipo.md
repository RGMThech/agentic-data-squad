# AGENTS.tipo.md — Squad de Data Analytics

> Complementa o `AGENTS.md` (núcleo comum a todas as squads) com as regras deste tipo de squad.
> Em conflito, vale o `AGENTS.md`.

## Gates neste tipo de squad

| Gate | Artefato | Quem prepara | Critério de aprovação |
|------|----------|--------------|------------------------|
| **G1 — Spec** | `specs/<id>/spec.md` | `analista-requisitos` | Regras de negócio corretas, métricas definidas, critérios de aceite testáveis, **zero dúvidas abertas** |
| **G2 — Design** | `specs/<id>/design.md` + contratos | `arquiteto-dados` | Modelo coerente, naming válido, contratos versionados, impacto em PII mapeado |
| **G3 — Produção** | Pull Request | `orquestrador` | CI verde, parecer do Revisor, relatório de QA, docs atualizadas, tarefas encerradas |

## Papéis e fronteiras

| Agente | Pode | Não pode |
|--------|------|----------|
| `orquestrador` | Quebrar trabalho, distribuir, consolidar, abrir PR | Escrever pipeline, aprovar gate |
| `analista-requisitos` | Escrever/atualizar spec, listar dúvidas | Decidir regra de negócio sozinho |
| `arquiteto-dados` | Modelar, definir contratos, escrever ADRs | Implementar pipelines |
| `eng-ingestao` | Implementar camada bronze | Alterar silver/gold, alterar contratos |
| `eng-transformacao` | Implementar silver/gold | Alterar bronze, alterar contratos |
| `qa-data-quality` | Escrever e rodar testes, reprovar entregas | Corrigir o código que testa |
| `analytics-bi` | Métricas, camada semântica, especificação de painéis | Alterar pipelines |
| `revisor` | Ler tudo, emitir parecer | Editar qualquer arquivo de código |
| `governanca-docs` | Documentação, catálogo, lineage, tags de PII | Alterar lógica |

**Segregação de funções:** quem escreve não testa, quem testa não corrige,
quem revisa não edita.

---

## Convenções obrigatórias

As convenções completas estão em `docs/naming-convention.md` e são validadas
automaticamente por `scripts/validate_naming.py`. Resumo:

- **Tabelas/arquivos de pipeline:** `<camada>_<dominio>__<entidade>`
  - camada ∈ `brz` (bronze), `slv` (silver), `gld` (gold)
  - exemplo: `slv_vendas__pedidos_itens`
- **Local:** `pipelines/<bronze|silver|gold>/<dominio>/<camada>_<dominio>__<entidade>.<sql|py>`
- **Colunas:** `snake_case`, sem acentos; sufixos semânticos:
  `_id`, `_dt` (data), `_ts` (timestamp), `_vl` (valor monetário), `_qt` (quantidade),
  `_fl` (flag booleana), `_cd` (código), `_ds` (descrição)
- **Specs:** `specs/<NNN>-<slug>/` (ex.: `specs/001-receita-diaria/`)
- **Contratos:** `contracts/<camada>_<dominio>__<entidade>.yaml`
- **Branches:** `feat/<NNN>-<slug>/<agente>`

---

## Dados e LGPD

- Toda coluna com dado pessoal deve ter `pii: true` e `classificacao` no contrato
  (LGPD: `pessoal`, `sensivel`, `anonimizado`, `publico`).
- Agentes **nunca** leem dados de produção não mascarados.

## Definição de pronto (DoD)

- [ ] Spec e design aprovados (G1, G2)
- [ ] Validadores do tipo passando (`python scripts/gates.py`: naming, contratos, gates)
- [ ] Testes de unidade e de qualidade passando
- [ ] Reconciliação com a fonte dentro da tolerância definida na spec
- [ ] Casos de ouro (`tests/golden/`) sem regressão
- [ ] Parecer do Revisor sem bloqueios
- [ ] Docs e lineage atualizados
- [ ] `specs/<feature>/entrega.md` lista todos os objetos construídos e onde estão
- [ ] Custo estimado registrado no PR

---
