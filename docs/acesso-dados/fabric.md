# Conectando a squad ao Microsoft Fabric

> Visão geral e outras plataformas: [acesso-dados.md](../acesso-dados.md).

A squad usa um **service principal do Microsoft Entra ID** e acessa o **SQL endpoint** do workspace (Warehouse e SQL analytics endpoint dos Lakehouses).

No Fabric, uma conexão SQL enxerga os itens de **um workspace**. Por isso, o desenho recomendado é um **workspace da squad** com:

| Item | Papel |
|------|-------|
| Warehouse `squad_dev` | sandbox: os agentes criam tabelas e views aqui |
| Lakehouse `fontes` | **atalhos (shortcuts)** para as tabelas que a squad pode ler; o SQL endpoint do Lakehouse é somente leitura |

Tempo estimado: **20 minutos**, com perfil de administrador do Fabric (para a configuração do tenant) e de administrador do workspace.

---

## 1. Registrar o aplicativo no Entra ID

1. Portal do Azure → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Nome: `squad-<nome-da-squad>` → **Register**.
3. Na tela do aplicativo, anote:
   - **Application (client) ID**: é o Client ID;
   - **Directory (tenant) ID**: é o Tenant ID.
4. **Certificates & secrets** → **New client secret** → validade de até 24 meses → copie o **Value** na hora (ele aparece uma única vez).

## 2. Liberar service principals no Fabric (uma vez por tenant)

Portal de administração do Fabric → **Tenant settings** → **Developer settings** → ative **Service principals can use Fabric APIs**. Prefira liberar só para um grupo de segurança que contenha o aplicativo da squad.

## 3. Montar o workspace da squad

1. Crie o workspace (ex.: `squad-vendas`) numa capacidade Fabric.
2. **New item** → **Warehouse** → nome `squad_dev`. No editor SQL dele, crie o schema da sandbox:
   ```sql
   CREATE SCHEMA agentes;
   ```
3. **New item** → **Lakehouse** → nome `fontes` → **New shortcut** → aponte para as tabelas de origem que a squad pode ler (outros Lakehouses ou Warehouses do OneLake, ADLS, S3).
4. **Manage access** → **Add people or groups** → o aplicativo `squad-<nome>` com o papel **Contributor**.

Assim a squad lê as fontes pelos atalhos e escreve só no próprio workspace. Não dê acesso de Contributor a workspaces de produção.

**Dados pessoais (LGPD):** aponte os atalhos para tabelas mascaradas, ou use views sem as colunas pessoais. A máscara do script é só uma camada extra.

## 4. Pegar a connection string

No workspace, abra o warehouse `squad_dev` → ícone de engrenagem (**Settings**) → **SQL endpoint** → copie a **SQL connection string**. Ela tem o formato `xxxxxxxx.datawarehouse.fabric.microsoft.com`.

## 5. Cadastrar no Squad Console

Squad Console → squad → **Configuração** → **Acesso a dados** → plataforma **Microsoft Fabric**:

| Campo | Valor |
|-------|-------|
| SQL connection string | `xxxxxxxx.datawarehouse.fabric.microsoft.com` |
| Warehouse padrão | `squad_dev` |
| Tenant ID | Directory (tenant) ID do passo 1 |
| Leitura | `fontes` (o Lakehouse com os atalhos) ou `fontes.dbo` |
| Escrita (sandbox) | `squad_dev.agentes` |
| Client ID | Application (client) ID do passo 1 |
| Client secret | Value do secret do passo 1 |

O GitHub Actions instala sozinho o driver ODBC 18 e o `pyodbc` quando a plataforma é Fabric.

## Problemas comuns

| Sintoma | Solução |
|---------|---------|
| "Client secret inválido ou expirado" | Gere um novo secret (passo 1) e cadastre de novo |
| "Aplicativo não encontrado no tenant" | Client ID ou Tenant ID trocados |
| "O Fabric recusou o login" | O aplicativo não está no workspace (passo 3.4) ou a configuração do tenant (passo 2) está desligada |
| Fonte não aparece | A tabela não tem atalho no Lakehouse `fontes`, ou está em outro workspace |
| Escrita recusada na sandbox | Confira o papel Contributor e se o schema `agentes` existe no warehouse |
