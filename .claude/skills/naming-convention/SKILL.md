---
name: naming-convention
description: Convenção de nomes obrigatória para tabelas, arquivos de pipeline, colunas, contratos, specs e branches. Use sempre que criar ou renomear qualquer um desses itens.
---

# Convenção de nomes

Referência completa: `docs/naming-convention.md`. Validador: `python scripts/validate_naming.py`.

## Tabelas e arquivos de pipeline

```
<camada>_<dominio>__<entidade>
```

- `camada`: `brz` | `slv` | `gld`
- `dominio`: minúsculo, sem acento, 2–20 caracteres, `[a-z][a-z0-9]*` (ex.: `vendas`, `clientes`, `credito`)
- separador **duplo** `__` entre domínio e entidade
- `entidade`: `snake_case` minúsculo (ex.: `pedidos_itens`, `receita_diaria_loja`)

Caminho: `pipelines/<bronze|silver|gold>/<dominio>/<nome>.<sql|py>`

| Errado | Certo |
|--------|-------|
| `pipelines/silver/Vendas/pedidos.sql` | `pipelines/silver/vendas/slv_vendas__pedidos.sql` |
| `gld_vendas_receita.sql` | `gld_vendas__receita_diaria_loja.sql` |
| `pipelines/gold/vendas/slv_vendas__x.sql` | camada do prefixo deve bater com a pasta |

## Colunas

`snake_case`, sem acentos, com sufixo semântico quando aplicável:

| Sufixo | Significado | Exemplo |
|--------|-------------|---------|
| `_id` | identificador | `cliente_id` |
| `_cd` | código | `loja_cd` |
| `_ds` | descrição | `produto_ds` |
| `_dt` | data | `venda_dt` |
| `_ts` | timestamp | `atualizacao_ts` |
| `_vl` | valor monetário | `receita_bruta_vl` |
| `_qt` | quantidade | `itens_qt` |
| `_fl` | flag booleana | `cancelado_fl` |
| `_pc` | percentual | `desconto_pc` |

Colunas técnicas começam com `_` (ex.: `_ingestao_ts`, `_lote_id`).

## Outros

- Spec: `specs/<NNN>-<slug>/` com NNN de 3 dígitos
- Contrato: `contracts/<nome_da_tabela>.yaml`
- Branch: `feat/<NNN>-<slug>/<agente>`
- ADR: `docs/adr/<NNNN>-<slug>.md`
