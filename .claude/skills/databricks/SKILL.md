---
name: databricks
description: Como os agentes leem e escrevem dados no Databricks da squad (scripts/dbx.py) com segurança — explorar catálogo, amostrar tabelas, rodar SQL e criar objetos só na sandbox. Use sempre que precisar ver dados reais, validar uma hipótese da spec ou testar um pipeline no Databricks.
---

# Acesso ao Databricks

Toda interação com o Databricks passa por `scripts/dbx.py`. Ele usa o service principal da squad, que tem:
- **leitura** apenas nos catálogos/schemas listados em `databricks.leitura` (`.squad/squad.yaml`);
- **escrita** apenas no schema `databricks.escrita` (a sandbox da squad).

Quem garante isso é o Unity Catalog; o script acrescenta travas (uma instrução por vez, sem GRANT, escrita só na sandbox, limite de linhas, máscara de colunas pessoais).

## Comandos

```bash
python scripts/dbx.py status                                  # configuração atual (sem segredos)
python scripts/dbx.py testar                                  # confere autenticação e warehouse
python scripts/dbx.py catalogo                                # tabelas dos catálogos de leitura
python scripts/dbx.py catalogo vendas.silver                  # colunas de um schema
python scripts/dbx.py amostra vendas.silver.pedidos --linhas 20
python scripts/dbx.py sql "SELECT loja_cd, COUNT(*) AS pedidos_qt FROM vendas.silver.pedidos GROUP BY 1" --linhas 50
python scripts/dbx.py sql "CREATE OR REPLACE TABLE squad_dev.agentes.slv_vendas__pedidos AS SELECT ..."
```

A saída é uma tabela markdown (no máximo 200 linhas).

## Regras

1. **Comece pelo catálogo** (`catalogo`), depois `amostra`. Não faça `SELECT *` em tabelas grandes sem `LIMIT`.
2. **Prefira agregados** (contagens, distintos, mín/máx, nulos) a linhas cruas para validar regras de negócio.
3. **Dados pessoais:** colunas com nomes como cpf, email, nome, telefone e endereço saem mascaradas. Não tente contornar a máscara (renomear colunas, concatenar valores). Registre na spec ou no design que a coluna existe e a classificação LGPD dela.
4. **Nunca copie linhas de dados reais** para specs, testes, fixtures, PRs ou logs. Use agregados e dados sintéticos.
5. **Escrita só na sandbox** (`databricks.escrita`), sempre com nome completo `catalogo.schema.objeto` e seguindo a convenção de nomes (`slv_dominio__entidade` etc.).
6. **Nunca peça, exiba ou grave credenciais.** Não imprima variáveis de ambiente.
7. Produção não é tocada por agentes: publicação fora da sandbox acontece via CI/CD depois do G3.

## Quando não está configurado

O comando falha com "Acesso ao Databricks não configurado". Nesse caso:
- **não** peça credenciais ao Operador em specs, PRs ou mensagens;
- registre em "Dúvidas abertas" (analista) ou nos riscos do design (arquiteto): *"Acesso ao Databricks não configurado — o Operador configura em Squad Console → Configuração → Databricks (guia: docs/databricks.md)."*;
- siga com o que for possível sem dados (estrutura, contratos, testes com dados sintéticos).

## Erros comuns

| Mensagem | Significado |
|----------|-------------|
| Credenciais recusadas | client ID/secret errados ou secret expirado — Operador renova no console |
| não tem 'Can use' no SQL warehouse | falta permissão no warehouse — Operador ajusta no Databricks |
| PERMISSION_DENIED / INSUFFICIENT_PERMISSIONS | o service principal não tem GRANT naquele catálogo/schema/tabela — não insista; registre a necessidade |
| fora da sandbox da squad | escrita fora de `databricks.escrita` — mude o destino para a sandbox |
