---
name: data-quality-tests
description: Como escrever testes de qualidade de dados da squad — testes derivados do contrato, reconciliação, casos de ouro e critérios de aceite. Use ao escrever ou revisar qualquer teste de pipeline.
---

# Testes de qualidade de dados

## Camadas de teste

| Tipo | Onde | Dados | Quando roda |
|------|------|-------|-------------|
| Unitário | `tests/unit/` | sintéticos, pequenos | todo commit (hook + CI) |
| Qualidade | `tests/quality/` | ambiente dev | após execução do pipeline |
| Golden | `tests/golden/` | entradas fixas, saída esperada conhecida | todo PR |

## Testes derivados do contrato (obrigatórios)

Para cada tabela com contrato, gere no mínimo:

1. **Unicidade** da chave (`chave` do contrato)
2. **Not null** para colunas `nulo: false`
3. **Domínio** para colunas com `valores_aceitos`
4. **Faixa** para colunas com `min`/`max`
5. **Integridade referencial** para colunas com `referencia`
6. **Frescor**: última carga dentro do `sla.frescor`
7. **Volume**: variação de linhas vs execução anterior dentro de `qualidade.variacao_volume_pc`

## Reconciliação

Compare camada N com camada N-1 (ou fonte):
- contagem de linhas (considerando dedup e filtros documentados)
- soma das medidas monetárias e de quantidade
- tolerância vem da spec (`tolerancia_reconciliacao_pc`); padrão 0%

## Critérios de aceite → teste

Cada critério `CA-xx` da spec vira um teste nomeado `test_ca_xx_<descricao>`.
O relatório de QA lista todos os CAs com ✅/❌ e evidência.

## Casos de ouro

Pasta `tests/golden/<feature>/` com `input/` (CSV/JSON pequenos), `expected/` e um `README.md` explicando o cenário de negócio.
São a memória de regressão da squad: um bug corrigido vira um caso de ouro.

## Anti-padrões (reprovam o QA)

- Teste sem asserção real
- Asserção que só checa "não vazio"
- Tolerância afrouxada para passar
- Dados reais/pessoais em fixtures
