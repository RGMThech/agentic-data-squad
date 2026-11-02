---
name: fluxos-atendimento
description: Como desenhar fluxos de atendimento e chatbot em YAML (nós, opções, escalonamento para humano) que o validador aceita. Use ao criar, testar ou revisar fluxos.
---

# Fluxos de atendimento

## Formato (`fluxos/<slug>.yaml`)
- `inicio`: id do primeiro nó.
- `nos`: mapa id → nó. Tipos:
  - `mensagem` e `acao`: têm `texto` e `proximo`;
  - `pergunta`: tem `texto` e `opcoes` (lista de `rotulo` + `proximo`);
  - `humano`: transfere para atendente (`fila` opcional);
  - `fim`: encerra.

## O validador exige
- nó inicial existente e todo `proximo` apontando para um nó que existe;
- todos os nós alcançáveis a partir do início;
- pelo menos um nó `humano` alcançável;
- nenhum nó sem saída (exceto `humano` e `fim`);
- `texto` com até 640 caracteres.

## Boas práticas
- Uma pergunta por mensagem; até 3 a 5 opções.
- "Falar com um atendente" disponível desde o primeiro menu.
- Depois de resolver, pergunte se resolveu; se não, escale.
- Peça só os dados necessários, e explique para quê.
