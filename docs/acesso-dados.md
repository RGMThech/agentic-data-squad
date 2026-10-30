# Acesso dos agentes aos dados

Os agentes podem consultar dados reais e testar pipelines em uma **sandbox**, usando uma identidade própria da squad e nunca o usuário de uma pessoa.

| Plataforma | Identidade da squad | Segredos (GitHub Actions) | Guia |
|------------|---------------------|---------------------------|------|
| Databricks | service principal (OAuth M2M) | `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` | [databricks.md](acesso-dados/databricks.md) |
| Snowflake | usuário de serviço com par de chaves | `SNOWFLAKE_PRIVATE_KEY` | [snowflake.md](acesso-dados/snowflake.md) |
| BigQuery | service account | `GCP_SA_KEY` | [bigquery.md](acesso-dados/bigquery.md) |
| Microsoft Fabric | service principal do Entra ID | `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET` | [fabric.md](acesso-dados/fabric.md) |
| dbt (em qualquer uma acima) | a mesma da plataforma | os mesmos | [dbt.md](acesso-dados/dbt.md) |

## O modelo de permissões é o mesmo em todas

| O quê | Permissão |
|-------|-----------|
| Fontes (`dados.leitura`) | somente leitura |
| Sandbox (`dados.escrita`: um ou mais `banco.schema`) | criar e alterar tabelas e views |
| Motor de consulta (warehouse, projeto de execução) | usar |
| Produção | nada além de leitura nas fontes liberadas |

Quem garante isso é a **plataforma**. O `scripts/dados.py` acrescenta travas:
- uma instrução por vez;
- nada de GRANT, REVOKE, EXECUTE ou CALL;
- escrita só na sandbox;
- limite de 200 linhas;
- máscara de colunas com cara de dado pessoal;
- no BigQuery, limite de GB processados por consulta.

## Como configurar

1. Siga o guia da plataforma para criar a identidade da squad, a sandbox e as permissões (15 a 20 minutos, com um perfil de administrador).
2. No Squad Console, abra a squad → **Configuração** → card **Acesso a dados**, escolha a plataforma e preencha os campos.
3. Clique em **Testar conexão**: o console autentica, roda uma consulta mínima e confere cada fonte e a sandbox.
4. Clique em **Testar e salvar**. As credenciais vão criptografadas para os segredos do GitHub Actions (o console não as guarda) e o restante vai para o bloco `dados` do `.squad/squad.yaml`:

```yaml
dados:
  plataforma: snowflake
  conexao: {conta: minhaorg-minhaconta, usuario: SQUAD_SVC, warehouse: SQUAD_WH, papel: SQUAD_ROLE}
  leitura: [vendas.silver, crm]
  escrita: squad_dev.agentes
  dbt: false
```

Uma squad usa **uma** plataforma por vez. Ao trocar, os segredos da plataforma anterior podem ser apagados no GitHub (Settings → Secrets and variables → Actions).

## Conferir

Peça a um agente pelo console: *"Liste as tabelas disponíveis e resuma o que encontrou."* Ele roda `python scripts/dados.py catalogo`.

Na sua máquina, com as variáveis de ambiente da plataforma definidas:

```bash
python scripts/dados.py status
python scripts/dados.py testar
python scripts/dados.py catalogo
```

## Renovação e corte de acesso

- **Credencial expirou:** gere uma nova na plataforma e cadastre de novo no console.
- **Cortar o acesso na hora:** desative a identidade da squad na plataforma ou remova as permissões. Os agentes param imediatamente.
- **Auditoria:** as consultas levam a marca `squad-agentica` (tag de consulta no Databricks e no Snowflake, label no BigQuery, nome da aplicação no Fabric).
