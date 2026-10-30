---
id: NNN
spec_versao: "1.0"
gerado_por: governanca-docs
gerado_em: AAAA-MM-DD
---

# Entrega — <título da feature>

## 1. Resumo
<3 a 5 linhas para quem é de negócio: o que foi construído e que decisão isso apoia.>

## 2. Objetos na plataforma

| Objeto | Camada | Onde está (banco.schema.objeto) | Tipo | Contrato | Pipeline | Testes |
|--------|--------|---------------------------------|------|----------|----------|--------|
| slv_dominio__entidade | silver | dev_dominio.silver.slv_dominio__entidade | tabela | contracts/slv_dominio__entidade.yaml | pipelines/silver/dominio/slv_dominio__entidade.sql | tests/quality/test_slv_dominio__entidade.py |

## 3. Métricas e painéis
| Métrica | Onde consultar | Definição |
|---------|----------------|-----------|

## 4. Como executar e atualizar
<ordem de execução dos pipelines, agendamento sugerido, parâmetros.>

## 5. Qualidade
<resumo do QA: testes, reconciliação, casos de ouro; link para qa-report.md.>

## 6. Pendências e próximos passos
<o que ficou fora do escopo, riscos conhecidos, publicação em produção via CI/CD.>
