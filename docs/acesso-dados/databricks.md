# Conectando a squad ao Databricks

> Visão geral e outras plataformas: [acesso-dados.md](../acesso-dados.md).

Os agentes acessam o Databricks com um **service principal** próprio da squad, nunca com o usuário de uma pessoa. As permissões são mínimas:

| O quê | Permissão | Por quê |
|-------|-----------|---------|
| Catálogos/schemas de origem | leitura (`USE CATALOG`, `USE SCHEMA`, `SELECT`) | explorar e validar os dados |
| Schema de sandbox (ex.: `squad_dev.agentes`) | criar e alterar tabelas | testar pipelines sem tocar em produção |
| SQL warehouse | `Can use` | rodar as consultas |

Quem garante isso é o **Unity Catalog**. Mesmo que um agente tente algo fora do escopo, o Databricks recusa. O script `scripts/dados.py` acrescenta travas extras: uma instrução por vez, nada de `GRANT`, escrita só na sandbox, limite de linhas e máscara de colunas pessoais.

Tempo estimado: **20 minutos**, com perfil de **admin do workspace**.

---

## 1. Criar o service principal

1. No workspace, clique no seu usuário (canto superior direito) → **Settings**.
2. **Identity and access** → ao lado de **Service principals**, clique em **Manage** → **Add service principal** → **Add new**.
3. Nome: `squad-<nome-da-squad>` (ex.: `squad-vendas-varejo`) → **Add**.
4. Abra o service principal criado e, na aba **Configurations**, marque:
   - **Databricks SQL access**
   - **Workspace access**
5. Anote o **Application ID** (UUID). Ele é o **Client ID**.

> **Azure Databricks:** o caminho é o mesmo. Use um service principal **gerenciado pelo Databricks** (opção *Add new*), que permite gerar o secret OAuth dentro do próprio Databricks, sem passar pelo Microsoft Entra ID.

## 2. Gerar o secret OAuth

1. Ainda no service principal → aba **Secrets** → **Generate secret**.
2. Validade: até 730 dias (anote a data para renovar).
3. Copie o **Secret** na hora: ele aparece uma única vez.

## 3. Dar acesso ao SQL warehouse

1. Menu lateral **SQL Warehouses** → escolha (ou crie) o warehouse da squad. Para agentes, um **Serverless** pequeno com *auto stop* de 10 minutos é suficiente e barato.
2. **Permissions** → adicione o service principal com **Can use**.
3. Anote o **Warehouse ID**: está na URL do warehouse (`/sql/warehouses/<ID>`) ou em **Connection details**.

## 4. Criar a sandbox e conceder as permissões (Unity Catalog)

Abra o **SQL Editor** com um usuário que possa conceder permissões e rode o bloco abaixo, trocando os nomes:
- `<APP_ID>`: o Application ID do passo 1
- `vendas`: o catálogo de origem

```sql
-- Sandbox da squad (onde os agentes podem criar tabelas)
CREATE CATALOG IF NOT EXISTS squad_dev;
CREATE SCHEMA  IF NOT EXISTS squad_dev.agentes;

GRANT USE CATALOG ON CATALOG squad_dev TO `<APP_ID>`;
GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA squad_dev.agentes TO `<APP_ID>`;

-- Fontes: somente leitura (repita para cada catálogo/schema que a squad pode ler)
GRANT USE CATALOG ON CATALOG vendas TO `<APP_ID>`;
GRANT USE SCHEMA, SELECT ON SCHEMA vendas.silver TO `<APP_ID>`;
-- arquivos brutos num Volume (CSV, JSON…):
-- GRANT READ VOLUME ON VOLUME vendas.brutos.arquivos TO `<APP_ID>`;
-- ou o catálogo inteiro:
-- GRANT USE SCHEMA, SELECT ON CATALOG vendas TO `<APP_ID>`;
```

**Dados pessoais (LGPD):** prefira dar acesso a schemas com dados **mascarados ou anonimizados**. Se a origem tem colunas pessoais, use *column masks* do Unity Catalog ou views sem essas colunas. O script também mascara na saída as colunas com nomes como cpf, email, nome e telefone, mas a proteção principal deve estar no Databricks.

Não conceda `ALL PRIVILEGES`, nem permissões em catálogos de produção além de leitura, nem `MANAGE`.

### Recomendado: um catálogo de trabalho para a squad

Para os agentes criarem sozinhos os schemas de que o design precisar (bronze, silver, gold…), libere o **catálogo** uma única vez. Os schemas que o service principal cria ficam com ele como dono, com todas as permissões, e você não precisa conceder mais nada a cada camada:

```sql
GRANT USE CATALOG, CREATE SCHEMA ON CATALOG dev_vendas TO `<APP_ID>`;

-- fontes dentro do mesmo catálogo: somente leitura (inclui arquivos em Volumes)
GRANT USE SCHEMA, SELECT, READ VOLUME ON SCHEMA dev_vendas.fontes TO `<APP_ID>`;
```

No console: **Leitura** `dev_vendas.fontes` e **Escrita** `dev_vendas` (o catálogo inteiro). As fontes continuam somente leitura: a plataforma não dá `MODIFY` nelas e o script recusa escrita em qualquer schema listado em Leitura.

Use um catálogo de desenvolvimento, nunca o de produção.

## 5. Cadastrar no Squad Console

Squad Console → abra a squad → **Configuração** → card **Acesso a dados** → plataforma **Databricks**:

| Campo | Valor |
|-------|-------|
| Host | URL do workspace, ex.: `https://adb-1234567890123456.7.azuredatabricks.net` |
| Warehouse ID | passo 3 |
| Leitura | catálogos ou `catalogo.schema` liberados, separados por vírgula (ex.: `vendas.silver, crm`) |
| Escrita (sandbox) | o catálogo de trabalho (`dev_vendas`) ou um schema (`squad_dev.agentes`) |
| Client ID | Application ID (passo 1) |
| Client secret | passo 2 |

Ao salvar, o console:
1. **testa a conexão** (autenticação, warehouse, leitura e sandbox) e mostra o resultado;
2. grava o client ID e o secret nos **segredos do GitHub Actions** do repositório (o console não guarda);
3. grava host, warehouse, leitura e escrita no bloco `dados` de `.squad/squad.yaml`.

## 6. Conferir

Peça a qualquer agente, pelo console, algo como: *"Liste as tabelas disponíveis no Databricks e resuma o que encontrou."* O agente roda `python scripts/dados.py catalogo`.

Para testar manualmente na sua máquina:

```bash
export DATABRICKS_CLIENT_ID=<APP_ID>
export DATABRICKS_CLIENT_SECRET=<SECRET>
python scripts/dados.py testar
python scripts/dados.py catalogo
```

---

## Renovação e revogação

- **Secret expira:** gere um novo (passo 2) e cadastre de novo no console. O anterior pode ser apagado no Databricks.
- **Cortar o acesso na hora:** desative o service principal no Databricks ou remova os `GRANT`s. Os agentes param de acessar imediatamente.
- **Auditoria:** consultas dos agentes ficam em `system.query.history`, com a tag `origem = squad-agentica`.

## Problemas comuns

| Sintoma | Solução |
|---------|---------|
| "Credenciais recusadas" | Client ID é o **Application ID** (não o nome); confira se o secret não expirou |
| "não tem 'Can use' no SQL warehouse" | Passo 3 |
| "SQL warehouse não encontrado" | Confira o Warehouse ID (só o ID, não a URL) |
| `PERMISSION_DENIED` ao ler uma tabela | Falta `USE CATALOG`/`USE SCHEMA`/`SELECT` naquele caminho (passo 4) |
| Consulta demora no primeiro uso | O warehouse estava parado e está ligando; serverless leva segundos, clássico pode levar minutos |
