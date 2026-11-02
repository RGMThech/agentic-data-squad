---
name: ia-responsavel
description: Checklist de IA responsável: vieses, explicabilidade, revisão humana, privacidade, segurança de LLM e uso indevido. Use ao especificar, desenhar, avaliar ou revisar soluções de IA.
---

# IA responsável

## Checklist
- **Finalidade:** o uso está claro e os usos fora do escopo estão escritos no model card?
- **Vieses:** há grupos (região, idade, gênero, renda) em que o erro pode ser maior? Meça por grupo.
- **Explicabilidade:** quem é afetado precisa entender a decisão? Prever explicação (importância de variáveis, fontes citadas).
- **Revisão humana:** decisões que afetam direitos de pessoas têm revisão humana (LGPD art. 20).
- **Privacidade:** minimização, base legal, nada identificável em prompts, avaliações e logs; retenção definida.
- **Segurança de LLM:** injeção de prompt (direta e por documentos), vazamento de instruções e dados, ferramentas com permissão mínima, saída validada.
- **Alucinação:** respostas citam a fonte; sem fonte, o sistema diz que não sabe.
- **Uso indevido:** como alguém poderia abusar? Quais limites e monitoramento?
- **Transparência:** o usuário sabe que está falando com uma IA.
