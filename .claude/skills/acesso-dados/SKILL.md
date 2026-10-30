---
name: acesso-dados
description: Como os agentes leem e escrevem dados reais da squad (Databricks, Snowflake, BigQuery ou Microsoft Fabric) com scripts/dados.py e, se habilitado, dbt — explorar o catálogo, amostrar tabelas, rodar SQL e criar objetos só na sandbox. Use sempre que precisar ver dados reais, validar uma hipótese da spec ou testar um pipeline.
---

# Acesso a dados

Toda consulta a dados reais passa por `scripts/dados.py`. O script usa a identidade da squad (service principal, usuário de serviço ou service account) na plataforma configurada em `.squad/squad.yaml` → `dados.plataforma`. Essa identidade tem:
- **leitura** apenas nas fontes listadas em `dados.leitura`;
- **escrita** apenas na sandbox `dados.escrita` (`banco.schema`).

Quem garante isso é a própria plataforma (Unity Catalog, papéis do Snowflake, IAM do BigQuery, permissões do Fabric). O script acrescenta travas: uma instrução por vez; nada de GRANT, EXECUTE ou CALL; escrita só na sandbox; limite de linhas; máscara de colunas pessoais; e, no BigQuery, limite de bytes processados.

## Nomes por plataforma

| Plataforma | banco | schema | Exemplo |
|------------|-------|--------|---------|
| Databricks | catálogo | schema | `vendas.silver.pedidos` |
| Snowflake | database | schema | `VENDAS.SILVER.PEDIDOS` (sem aspas) |
| BigQuery | projeto | dataset | `` `meu-projeto.vendas.pedidos` `` |
| Fabric | warehouse ou lakehouse | schema | `vendas.dbo.pedidos` |

Use sempre o nome completo `banco.schema.tabela`. Escreva o SQL no dialeto da plataforma (`LIMIT` em Databricks/Snowflake/BigQuery; `TOP` no Fabric).

## Comandos

```bash
python scripts/dados.py status                                 # plataforma e configuração (sem segredos)
python scripts/dados.py testar                                 # confere autenticação e consulta mínima
python scripts/dados.py catalogo                               # tabelas das fontes de leitura
python scripts/dados.py catalogo vendas.silver                 # colunas de um schema
python scripts/dados.py amostra vendas.silver.pedidos --linhas 20
python scripts/dados.py sql "SELECT loja_cd, COUNT(*) AS pedidos_qt FROM vendas.silver.pedidos GROUP BY 1" --linhas 50
python scripts/dados.py sql "CREATE OR REPLACE TABLE squad_dev.agentes.slv_vendas__pedidos AS SELECT ..."
```

A saída é uma tabela markdown (no máximo 200 linhas). No BigQuery, `amostra` não tem custo (lê a tabela sem rodar consulta) e o rodapé mostra os GB processados de cada `sql`.

## Arquivos em Volumes (Databricks)

Arquivos brutos (CSV, JSON, Parquet) num Volume do Unity Catalog são lidos pelo mesmo script:

```bash
python scripts/dados.py sql "LIST '/Volumes/eleicoes/brutos/arquivos/'"
python scripts/dados.py sql "SELECT * FROM read_files('/Volumes/eleicoes/brutos/arquivos/candidatos.csv', format => 'csv', header => true, sep => ';', encoding => 'ISO-8859-1') LIMIT 5"
python scripts/dados.py sql "SELECT COUNT(*) AS linhas_qt FROM read_files('/Volumes/eleicoes/brutos/arquivos/candidatos.csv', format => 'csv', header => true, sep => ';')"
```

O service principal precisa de `READ VOLUME` no Volume. Para inventariar arquivos, prefira `LIST` e contagens; amostras saem mascaradas como qualquer consulta.

## dbt

Se `dados.dbt: true`, o workflow instala o adaptador dbt da plataforma e gera o perfil **`squad`** (target `sandbox`, schema de destino = `dados.escrita`) fora do repositório. No projeto dbt:
- `dbt_project.yml` deve usar `profile: squad`;
- rode `dbt build`, `dbt test`, `dbt compile` normalmente; os modelos são criados na sandbox;
- **nunca** crie ou versione `profiles.yml` no repositório, nem coloque credenciais em `dbt_project.yml` ou macros;
- `dbt run-operation` e hooks que alterem permissões (GRANT) são proibidos, como no SQL direto.

## Regras

1. **Comece pelo catálogo** (`catalogo`), depois `amostra`. Não faça `SELECT *` em tabelas grandes sem `LIMIT`/`TOP` e filtros.
2. **Prefira agregados** (contagens, distintos, mín/máx, nulos) a linhas cruas para validar regras de negócio.
3. **Custo:** no BigQuery filtre por partição e selecione só as colunas necessárias; se a consulta passar do limite de GB, ela é barrada. Não tente contornar o limite.
4. **Dados pessoais:** colunas com nomes como cpf, email, nome, telefone e endereço saem mascaradas. Não tente contornar a máscara (renomear colunas, concatenar valores). Registre na spec ou no design que a coluna existe e a classificação LGPD dela.
5. **Nunca copie linhas de dados reais** para specs, testes, fixtures, PRs ou logs. Use agregados e dados sintéticos.
6. **Escrita só na sandbox** (`dados.escrita`), sempre com nome completo e seguindo a convenção de nomes (`slv_dominio__entidade` etc.).
7. **Nunca peça, exiba ou grave credenciais.** Não imprima variáveis de ambiente nem o conteúdo de arquivos de perfil.
8. Produção não é tocada por agentes: publicação fora da sandbox acontece via CI/CD depois do G3.

## Quando não está configurado

O comando falha com "Acesso a dados não configurado" (ou "Acesso ao <plataforma> não configurado", dizendo o que falta). Nesse caso:
- **não** peça credenciais ao Operador em specs, PRs ou mensagens;
- registre em "Dúvidas abertas" (analista) ou nos riscos do design (arquiteto): *"Acesso a dados não configurado — o Operador configura em Squad Console → Configuração → Acesso a dados (guia: docs/acesso-dados.md)."*;
- siga com o que for possível sem dados (estrutura, contratos, testes com dados sintéticos).

## Erros comuns

| Mensagem | Significado |
|----------|-------------|
| Credenciais recusadas / Chave recusada / Client secret inválido | credencial errada ou expirada: o Operador renova no console |
| sem permissão / PERMISSION_DENIED / does not exist or not authorized | a identidade da squad não tem acesso àquele objeto: não insista, registre a necessidade |
| fora da sandbox da squad | escrita fora de `dados.escrita`: mude o destino para a sandbox |
| processaria mais que o limite de N GB | consulta cara no BigQuery: filtre partições e colunas |
| Driver do Fabric ausente | só ocorre fora do GitHub Actions; no workflow o driver é instalado sozinho |
