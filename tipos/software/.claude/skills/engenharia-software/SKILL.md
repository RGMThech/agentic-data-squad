---
name: engenharia-software
description: Boas práticas de engenharia de software da squad: estrutura de código, testes, commits, revisão e ADRs. Use ao implementar, testar ou revisar qualquer código.
---

# Engenharia de software

## Código
- Siga a stack e o estilo que o repositório já usa (`docs/arquitetura.md`). Linter e formatador do projeto valem como regra.
- Funções pequenas, nomes que dizem a intenção, sem código morto nem comentário que repete o código.
- Erros: trate onde dá para agir; senão, propague com contexto. Nunca engula exceção.
- Configuração por variável de ambiente; nada fixo no código que mude por ambiente.

## Testes
- Todo critério de aceite (`CA-xx`) tem teste automatizado que cita o ID.
- Pirâmide: muitos testes de unidade, alguns de integração, poucos ponta a ponta.
- Testes determinísticos: sem depender de rede externa, hora atual ou ordem de execução.
- Dados de teste sintéticos.

## Commits e PR
- Conventional Commits: `feat(api): cria endpoint de reembolso`.
- Um commit por mudança lógica; o PR descreve o que mudou, como testar e o risco.

## ADR
Decisão difícil de desfazer (banco, framework, padrão de integração) → `docs/adr/NNNN-<slug>.md` com contexto, opções, decisão e consequências.
