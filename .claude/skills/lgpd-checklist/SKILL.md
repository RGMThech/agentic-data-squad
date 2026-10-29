---
name: lgpd-checklist
description: Checklist de LGPD e proteção de dados para modelagem, código, testes e documentação. Use ao modelar tabelas com dados de pessoas, ao revisar código e ao documentar colunas.
---

# Checklist LGPD

> Este checklist orienta a engenharia. Não substitui análise do DPO/jurídico.

## Classificação de colunas (obrigatória no contrato)

| `classificacao` | Exemplo | Tratamento mínimo |
|-----------------|---------|-------------------|
| `publico` | UF, categoria de produto | nenhum |
| `pessoal` | nome, e-mail, CPF, telefone, endereço | `pii: true`, acesso restrito, mascarar fora de prod |
| `sensivel` | saúde, biometria, religião, origem racial, opinião política | `pii: true`, base legal registrada, acesso mínimo, evitar em gold |
| `anonimizado` | hash irreversível com salt, agregados sem reidentificação | documentar técnica |

## Na modelagem
- [ ] Minimização: a coluna pessoal é realmente necessária para a spec?
- [ ] Gold e painéis sem dado pessoal, salvo exigência da spec
- [ ] Finalidade e base legal citadas no design quando houver `sensivel`
- [ ] Retenção definida no contrato (`retencao_dias`)

## No código
- [ ] Nenhum dado pessoal em logs, mensagens de erro ou prints
- [ ] Nenhuma credencial em código
- [ ] Pseudonimização aplicada na silver quando o design pedir

## Nos testes
- [ ] Apenas dados sintéticos (ex.: Faker com seed fixa) ou mascarados
- [ ] CPFs de teste gerados e inválidos para uso real

## Na documentação
- [ ] Tags de PII aplicadas no catálogo
- [ ] Owner e finalidade descritos
