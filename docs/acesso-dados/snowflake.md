# Conectando a squad ao Snowflake

> Visão geral e outras plataformas: [acesso-dados.md](../acesso-dados.md).

A squad usa um **usuário de serviço** (`TYPE = SERVICE`, sem senha) que autentica por **par de chaves RSA**, com um papel próprio:

| O quê | Permissão |
|-------|-----------|
| Databases/schemas de origem | `USAGE` + `SELECT` |
| Schema de sandbox (ex.: `SQUAD_DEV.AGENTES`) | `USAGE`, `CREATE TABLE`, `CREATE VIEW` |
| Virtual warehouse | `USAGE` |

Tempo estimado: **15 minutos**, com um papel que crie usuários e conceda permissões (`ACCOUNTADMIN`, ou `USERADMIN` + `SECURITYADMIN` + `SYSADMIN`).

---

## 1. Gerar o par de chaves (na sua máquina)

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out squad_rsa_key.p8 -nocrypt
openssl rsa -in squad_rsa_key.p8 -pubout -out squad_rsa_key.pub
```

- `squad_rsa_key.p8` é a **chave privada**: vai para o console no passo 4 e depois pode ser apagada da máquina. Não envie por e-mail ou chat.
- `squad_rsa_key.pub` é a **chave pública**: vai para o Snowflake no passo 2. Copie só o conteúdo entre as linhas `BEGIN` e `END`, sem quebras de linha.

## 2. Criar papel, usuário, warehouse e sandbox

Em uma worksheet do Snowsight, troque `<CHAVE_PUBLICA>` e os nomes das fontes:

```sql
USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS SQUAD_ROLE;
CREATE USER IF NOT EXISTS SQUAD_SVC
  TYPE = SERVICE
  DEFAULT_ROLE = SQUAD_ROLE
  RSA_PUBLIC_KEY = '<CHAVE_PUBLICA>';
GRANT ROLE SQUAD_ROLE TO USER SQUAD_SVC;

-- warehouse pequeno, que desliga sozinho
CREATE WAREHOUSE IF NOT EXISTS SQUAD_WH
  WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
GRANT USAGE ON WAREHOUSE SQUAD_WH TO ROLE SQUAD_ROLE;

-- sandbox da squad
CREATE DATABASE IF NOT EXISTS SQUAD_DEV;
CREATE SCHEMA IF NOT EXISTS SQUAD_DEV.AGENTES;
GRANT USAGE ON DATABASE SQUAD_DEV TO ROLE SQUAD_ROLE;
GRANT USAGE, CREATE TABLE, CREATE VIEW ON SCHEMA SQUAD_DEV.AGENTES TO ROLE SQUAD_ROLE;

-- fontes: somente leitura (repita para cada schema)
GRANT USAGE ON DATABASE VENDAS TO ROLE SQUAD_ROLE;
GRANT USAGE ON SCHEMA VENDAS.SILVER TO ROLE SQUAD_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA VENDAS.SILVER TO ROLE SQUAD_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA VENDAS.SILVER TO ROLE SQUAD_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA VENDAS.SILVER TO ROLE SQUAD_ROLE;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA VENDAS.SILVER TO ROLE SQUAD_ROLE;
```

**Para os agentes criarem as camadas sozinhos** (bronze, silver, gold…), conceda `CREATE SCHEMA` no database de trabalho e informe em Escrita só `SQUAD_DEV`:

```sql
GRANT USAGE, CREATE SCHEMA ON DATABASE SQUAD_DEV TO ROLE SQUAD_ROLE;
```

**Custo:** para um teto mensal, crie um *resource monitor* e associe ao `SQUAD_WH`.

**Dados pessoais (LGPD):** prefira liberar schemas com dados mascarados. Use *masking policies* nas colunas pessoais; a máscara do script é só uma camada extra.

Não conceda `OWNERSHIP` em objetos de produção, `MANAGE GRANTS` nem papéis administrativos ao `SQUAD_ROLE`.

## 3. Achar o identificador da conta

No Snowsight, clique no seu nome (canto inferior esquerdo) → **Account** → **View account details**. Copie o **Account identifier**, no formato `MINHAORG-MINHACONTA`.

Também serve o começo da URL: em `https://minhaorg-minhaconta.snowflakecomputing.com`, o identificador é `minhaorg-minhaconta`.

## 4. Cadastrar no Squad Console

Squad Console → squad → **Configuração** → **Acesso a dados** → plataforma **Snowflake**:

| Campo | Valor |
|-------|-------|
| Conta | `minhaorg-minhaconta` |
| Usuário | `SQUAD_SVC` |
| Warehouse | `SQUAD_WH` |
| Papel | `SQUAD_ROLE` |
| Leitura | `vendas.silver, crm` |
| Escrita (sandbox) | `squad_dev.agentes` |
| Chave privada | conteúdo inteiro do `squad_rsa_key.p8`, com as linhas `BEGIN`/`END` |

## Problemas comuns

| Sintoma | Solução |
|---------|---------|
| "Chave recusada" / `JWT token is invalid` | Usuário ou conta errados, ou a chave pública registrada não é par da privada. Confira com `DESC USER SQUAD_SVC` (campo `RSA_PUBLIC_KEY_FP`) |
| "does not exist or not authorized" | Falta `USAGE` no database/schema ou `SELECT` na tabela para o `SQUAD_ROLE` |
| Problema com o warehouse | Falta `GRANT USAGE ON WAREHOUSE` ou o nome está errado |
| Bloqueio por IP | A conta tem *network policy*: libere os IPs do GitHub Actions e do servidor do console, ou crie uma política específica para o `SQUAD_SVC` |
| "chave protegida por senha" | Gere a chave com `-nocrypt` (passo 1) |

**Rotação de chave:** gere um novo par, registre com `ALTER USER SQUAD_SVC SET RSA_PUBLIC_KEY_2 = '...'`, cadastre a nova privada no console e depois remova a antiga com `ALTER USER SQUAD_SVC UNSET RSA_PUBLIC_KEY`.
