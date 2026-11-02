---
name: lgpd-checklist
description: Checklist de LGPD e proteção de dados pessoais para qualquer tipo de squad — especificação, design, código, conteúdo, testes e documentação. Use sempre que o trabalho envolver dados de pessoas (clientes, leads, usuários, participantes de pesquisa, colaboradores).
---

# Checklist LGPD

> Este checklist orienta a squad. Não substitui análise do DPO/jurídico.

## Para todos os tipos de squad
- [ ] **Finalidade:** o uso do dado pessoal está ligado a um objetivo escrito na spec.
- [ ] **Minimização:** só o dado pessoal necessário para essa finalidade.
- [ ] **Base legal** registrada no design quando houver dado pessoal (consentimento, contrato, legítimo interesse…); sempre que houver dado **sensível** (saúde, biometria, religião, origem racial, opinião política, vida sexual, filiação sindical).
- [ ] **Nada de dado real no repositório:** specs, tarefas, peças, artigos, prompts, testes e PRs usam exemplos fictícios ou anonimizados (P1, P2…; `nome@exemplo.com.br`). Os validadores procuram CPF, e-mail e telefone.
- [ ] **Logs e mensagens de erro** sem dado pessoal, senha ou token.
- [ ] **Direitos do titular:** se a entrega cria ou guarda dado pessoal, o design diz como atender acesso, correção e exclusão.
- [ ] **Decisão automatizada** que afete pessoas prevê revisão humana (art. 20).
- [ ] **Comunicação com pessoas** (e-mail, WhatsApp, chatbot): só com base legal e com forma simples de sair.

## Classificação de dados

| `classificacao` | Exemplo | Tratamento mínimo |
|-----------------|---------|-------------------|
| `publico` | UF, categoria de produto | nenhum |
| `pessoal` | nome, e-mail, CPF, telefone, endereço | acesso restrito, mascarar fora de produção |
| `sensivel` | saúde, biometria, religião, origem racial, opinião política | base legal registrada, acesso mínimo, evitar em relatórios |
| `anonimizado` | hash irreversível com salt, agregados sem reidentificação | documentar técnica |

## Em squads de dados (contratos, pipelines, painéis)
- [ ] Toda coluna pessoal com `pii: true` e `classificacao` no contrato
- [ ] Gold e painéis sem dado pessoal, salvo exigência da spec
- [ ] Retenção definida no contrato (`retencao_dias`)
- [ ] Pseudonimização aplicada na silver quando o design pedir
- [ ] Tags de PII aplicadas no catálogo; owner e finalidade descritos

## Nos testes
- [ ] Apenas dados sintéticos (ex.: Faker com seed fixa) ou mascarados
- [ ] CPFs de teste gerados e inválidos para uso real
