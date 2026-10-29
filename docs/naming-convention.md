# Convenção de nomes

Este documento é a referência completa. O resumo operacional para os agentes está na skill `naming-convention`. O validador é `scripts/validate_naming.py`.

## Por que tão rígida

Naming inconsistente é uma das principais causas de dívida em data lakes: tabelas duplicadas, métricas divergentes e catálogos impossíveis de navegar. Com agentes gerando código em escala, a convenção precisa ser **verificada por máquina**, não por revisão humana.

## Tabelas

```
<camada>_<dominio>__<entidade>
```

| Parte | Regra | Exemplos |
|-------|-------|----------|
| camada | `brz`, `slv` ou `gld` | `slv` |
| dominio | `[a-z][a-z0-9]{1,19}`, sem acento | `vendas`, `credito`, `clientes` |
| separador | `__` (duplo) | |
| entidade | `snake_case` minúsculo | `pedidos_itens`, `receita_diaria_loja` |

O separador duplo permite separar domínio e entidade sem ambiguidade, mesmo quando a entidade tem vários termos.

### Mapeamento para catálogo

O template é agnóstico. Escolha uma das opções e registre num ADR:

| Plataforma | Opção A (nome único) | Opção B (hierarquia) |
|------------|----------------------|----------------------|
| Databricks Unity Catalog | `<catalogo>.<schema>.slv_vendas__pedidos` | catálogo = domínio, schema = camada, tabela = entidade |
| Snowflake | `<db>.<schema>.SLV_VENDAS__PEDIDOS` | db = domínio, schema = camada |
| BigQuery | `<projeto>.<dataset>.slv_vendas__pedidos` | dataset = `<dominio>_<camada>` |

Mesmo na opção B, mantenha o **nome do arquivo** do pipeline no padrão completo: é o que o validador usa.

## Colunas

| Sufixo | Tipo esperado | Exemplo |
|--------|---------------|---------|
| `_id` | string/inteiro | `cliente_id` |
| `_cd` | string | `loja_cd` |
| `_ds` | string | `produto_ds` |
| `_dt` | date | `venda_dt` |
| `_ts` | timestamp | `atualizacao_ts` |
| `_vl` | decimal(18,2) | `receita_bruta_vl` |
| `_qt` | inteiro | `itens_qt` |
| `_fl` | boolean | `cancelado_fl` |
| `_pc` | decimal | `desconto_pc` |

- Colunas técnicas começam com `_`: `_ingestao_ts`, `_fonte_cd`, `_arquivo_ds`, `_lote_id`.
- Proibido: acentos, espaços, hífen, CamelCase, abreviações não listadas.

## Specs, contratos, branches e ADRs

| Item | Padrão | Exemplo |
|------|--------|---------|
| Spec | `specs/NNN-slug/` | `specs/001-inadimplencia-mensal/` |
| Contrato | `contracts/<tabela>.yaml` | `contracts/gld_credito__inadimplencia_mensal.yaml` |
| Branch | `feat/NNN-slug/<agente>` | `feat/001-inadimplencia-mensal/eng-transformacao` |
| ADR | `docs/adr/NNNN-slug.md` | `docs/adr/0002-scd2-clientes.md` |
