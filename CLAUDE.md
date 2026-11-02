# CLAUDE.md

Leia e siga integralmente:
- [`AGENTS.md`](./AGENTS.md) — a constituição comum a todas as squads;
- [`AGENTS.tipo.md`](./AGENTS.tipo.md) — os papéis, convenções e a definição de pronto deste tipo de squad.

Atalhos:

- Fluxo de trabalho: skill `sdd-workflow`
- LGPD: skill `lgpd-checklist`
- Acesso a dados (Databricks, Snowflake, BigQuery, Fabric, dbt): skill `acesso-dados` e `docs/acesso-dados.md`
- Agentes e skills do tipo: `.claude/agents/` e `.claude/skills/`
- Configuração do tipo (papéis, validadores): `.squad/tipo.yaml`

Antes de encerrar qualquer tarefa que altere arquivos, rode:

```bash
python scripts/gates.py
```
