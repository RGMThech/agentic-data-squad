# CLAUDE.md

Leia e siga integralmente o arquivo [`AGENTS.md`](./AGENTS.md) — ele é a constituição desta squad.

Atalhos:

- Fluxo de trabalho: skill `sdd-workflow`
- Convenção de nomes: skill `naming-convention` e `docs/naming-convention.md`
- Testes de qualidade: skill `data-quality-tests`
- LGPD: skill `lgpd-checklist`
- Acesso a dados (Databricks, Snowflake, BigQuery, Fabric, dbt): skill `acesso-dados` e `docs/acesso-dados.md`
- Agentes disponíveis: `.claude/agents/`

Antes de encerrar qualquer tarefa que altere arquivos, rode:

```bash
python scripts/validate_naming.py
python scripts/check_contracts.py
python scripts/check_spec.py
```
