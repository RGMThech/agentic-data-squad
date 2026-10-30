# dbt na squad

> Visão geral e outras plataformas: [acesso-dados.md](../acesso-dados.md).

O dbt não é uma plataforma de dados: ele roda **sobre** uma delas. Para a squad usar dbt:

1. Configure o acesso à plataforma (Databricks, Snowflake, BigQuery ou Fabric) pelo guia correspondente.
2. No Squad Console → **Configuração** → **Acesso a dados**, marque **Usar dbt** e salve.

A cada execução de agente, o workflow:
- instala o adaptador da plataforma (`dbt-databricks`, `dbt-snowflake`, `dbt-bigquery` ou `dbt-fabric`);
- gera o `profiles.yml` **fora do repositório**, com o perfil `squad` e o target `sandbox`. O schema de destino é a sandbox (`dados.escrita`) e as credenciais vêm dos segredos via `env_var()`;
- define `DBT_PROFILES_DIR` para os agentes.

## No projeto dbt

```yaml
# dbt_project.yml
name: squad_vendas
profile: squad
```

Os agentes rodam `dbt build`, `dbt test` e `dbt compile` normalmente. Tudo é criado na sandbox.

## Segurança

- O dbt executa SQL **sem** as travas do `scripts/dados.py`. Quem garante "leitura nas fontes, escrita só na sandbox" são as permissões da plataforma. Por isso, siga à risca o modelo de permissões do guia da plataforma.
- `profiles.yml` nunca é versionado; o `.gitignore` e o script impedem que ele seja gerado dentro do repositório.
- Schemas customizados (`+schema:`) viram `<sandbox>_<nome>`. Se a identidade da squad não puder criar schemas, mantenha tudo no schema da sandbox.
- Publicar modelos em produção é tarefa do CI/CD depois do G3, com outra identidade.

## Para rodar o mesmo perfil na sua máquina

```bash
# com as variáveis de ambiente da plataforma definidas
python scripts/dados.py dbt-profile --saida ~/.dbt-squad
DBT_PROFILES_DIR=~/.dbt-squad dbt debug
```
