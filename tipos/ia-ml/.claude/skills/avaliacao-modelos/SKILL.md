---
name: avaliacao-modelos
description: Como avaliar modelos clássicos e LLMs: divisão de dados, linha de base, métricas, limiares, métricas por grupo, testes adversariais e registro em eval.yaml. Use ao desenhar, treinar ou avaliar.
---

# Avaliação de modelos

## Regras
- Limiar definido no design (G2), antes de treinar.
- Treino → ajuste na validação → **uma** avaliação final no teste.
- Sempre comparar com uma linha de base simples.
- Registrar semente, versão dos dados e do código.

## Métricas usuais
| Problema | Métricas |
|----------|----------|
| Classificação | precisão, recall, F1, AUC-PR (classes desbalanceadas), matriz de confusão |
| Regressão | MAE, RMSE, MAPE, erro por faixa |
| Ranking / busca | NDCG@k, recall@k, MRR |
| LLM / RAG | fidelidade às fontes, relevância da resposta, recall da recuperação, taxa de alucinação, taxa de recusa indevida |
| Operação | latência p95, custo por chamada |

## LLM
- Casos de avaliação sintéticos ou anonimizados, cobrindo o caminho feliz, perguntas fora do escopo, injeção de prompt e pedidos de dado pessoal.
- Avaliação automática (LLM como juiz) só com rubrica escrita e amostra conferida por humano.

## eval.yaml
Uma entrada por métrica com `valor`, `limiar` e `direcao`. `resultado: aprovado` só se todas passarem — o validador confere.
