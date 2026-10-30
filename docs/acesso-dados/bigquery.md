# Conectando a squad ao BigQuery

> Visão geral e outras plataformas: [acesso-dados.md](../acesso-dados.md).

A squad usa uma **service account** própria:

| O quê | Papel (IAM) |
|-------|-------------|
| Projeto que executa as consultas | `BigQuery Job User` |
| Datasets de origem | `BigQuery Data Viewer` (no dataset, não no projeto) |
| Dataset de sandbox (ex.: `meu-projeto.squad_agentes`) | `BigQuery Data Editor` |

Tempo estimado: **15 minutos**, com perfil de administrador do projeto.

---

## 1. Criar a service account

1. Console do Google Cloud → selecione o projeto → **IAM & Admin** → **Service Accounts** → **Create service account**.
2. Nome: `squad-<nome-da-squad>` → **Create and continue**.
3. Papel: **BigQuery Job User** → **Done**.
4. Anote o e-mail, no formato `squad-<nome>@<projeto>.iam.gserviceaccount.com`.

## 2. Criar a sandbox e dar acesso às fontes

No editor de consultas do BigQuery, troque os nomes:

```sql
-- sandbox da squad (use a mesma região das fontes)
CREATE SCHEMA IF NOT EXISTS `meu-projeto.squad_agentes` OPTIONS (location = 'US');

GRANT `roles/bigquery.dataEditor` ON SCHEMA `meu-projeto.squad_agentes`
  TO "serviceAccount:squad-vendas@meu-projeto.iam.gserviceaccount.com";

-- fontes: somente leitura (repita para cada dataset)
GRANT `roles/bigquery.dataViewer` ON SCHEMA `meu-projeto.vendas`
  TO "serviceAccount:squad-vendas@meu-projeto.iam.gserviceaccount.com";
```

**Para os agentes criarem os datasets sozinhos**, use um projeto de desenvolvimento só da squad, dê à service account o papel `BigQuery User` nele (permite criar datasets, dos quais ela vira dona) e informe em Escrita só o projeto (`meu-projeto-dev`).

Se preferir a interface: abra o dataset → **Sharing** → **Permissions** → **Add principal**.

**Dados pessoais (LGPD):** prefira datasets com dados mascarados. Use *policy tags* (Data Catalog) ou *authorized views* para colunas pessoais.

## 3. Gerar a chave JSON

Service account → aba **Keys** → **Add key** → **Create new key** → **JSON**. Um arquivo `.json` é baixado: ele vai para o console no passo 4 e depois pode ser apagado da máquina.

> Se aparecer "Service account key creation is disabled", a organização bloqueia chaves pela política `iam.disableServiceAccountKeyCreation`. Peça ao administrador uma exceção para este projeto.

## 4. Cadastrar no Squad Console

Squad Console → squad → **Configuração** → **Acesso a dados** → plataforma **BigQuery**:

| Campo | Valor |
|-------|-------|
| Projeto | projeto que executa (e paga) as consultas, ex.: `meu-projeto` |
| Região | região dos datasets: `US`, `EU`, `southamerica-east1` |
| Limite por consulta (GB) | teto de bytes processados por consulta; o padrão é 10 |
| Leitura | `meu-projeto.vendas, meu-projeto.crm` |
| Escrita (sandbox) | `meu-projeto.squad_agentes` |
| Chave da service account | conteúdo inteiro do arquivo JSON |

## Custos

- Cada consulta tem teto de bytes processados (**Limite por consulta**). Acima dele, o BigQuery recusa a consulta sem cobrar.
- `amostra` não roda consulta (lê a tabela direto) e não custa nada.
- O rodapé de cada `sql` mostra os GB processados.

## Problemas comuns

| Sintoma | Solução |
|---------|---------|
| "Chave da service account recusada" | A chave foi apagada ou desativada: gere outra |
| "Sem permissão" | Falta `Job User` no projeto de execução ou `Data Viewer` no dataset |
| "não encontrado" | Nome de projeto ou dataset errado, ou região diferente da informada |
| "processaria mais que o limite" | Filtre por partição e selecione só as colunas necessárias |
