# Playbook do Operador Humano

Você é o único humano da squad. Seu trabalho não é escrever código. É garantir que **a intenção está certa** e que **o harness impede o erro**.

## Sua rotina

| Momento | Você faz | Tempo típico |
|---------|----------|--------------|
| Nova demanda | Descreve o problema de negócio ao `analista-requisitos` | 5–10 min |
| G1 — Spec | Responde as dúvidas, confere regras, métricas e critérios de aceite, aprova | 15–30 min |
| G2 — Design | Confere modelo, contratos, PII e custo, aprova | 15–30 min |
| Durante a execução | Só responde escalonamentos (4ª falha de QA ou mudança de escopo) | eventual |
| G3 — PR | Lê o resumo, o relatório de QA e o parecer do Revisor, aprova o merge | 10–20 min |
| Pós-entrega | Transforma cada correção em regra do harness | 10 min |

## Como pedir uma feature

```
Use o agente analista-requisitos para criar a spec da próxima feature.
Problema: <o que está doendo no negócio>
Quem usa: <público>
Decisão que será tomada com isso: <...>
Fontes que conheço: <...>
Prazo/SLA: <...>
```

Depois de aprovar a spec:

```
Use o agente arquiteto-dados para desenhar a spec <id>.
```

Depois de aprovar o design:

```
Use o agente orquestrador para executar a feature <id> até o G3.
```

## Como aprovar um gate

No front matter do artefato, altere você mesmo:

```yaml
status: aprovado
aprovado_por: <seu nome>
aprovado_em: AAAA-MM-DD
```

Nenhum agente pode fazer isso. O `check_spec.py` exige esses campos e bloqueia tarefas sem os dois gates aprovados.

## O que revisar em cada gate

**G1 — Spec**
- Cada métrica tem fórmula, grão, filtro e tratamento de nulos?
- Os critérios de aceite são testáveis por máquina?
- A seção "Dúvidas abertas" está vazia?
- O que está fora de escopo está explícito?

**G2 — Design**
- O grão de cada tabela está claro?
- Toda coluna pessoal está classificada? Dado pessoal chega à gold sem necessidade?
- A carga é incremental e idempotente?
- O custo estimado é aceitável?

**G3 — PR**
- CI verde?
- Parecer do Revisor sem bloqueios?
- Todos os critérios de aceite ✅ no relatório de QA?
- Algum número conhecido do negócio bate? (rode `semantic/validacoes/<id>.sql`)

## Quando um agente errar

Não corrija o código você mesmo. Pergunte: **qual regra teria evitado isso?**

| Tipo de erro | Onde vira regra |
|--------------|-----------------|
| Regra de negócio mal interpretada | template da spec (nova pergunta obrigatória) |
| Padrão de código ruim | `AGENTS.md` ou skill |
| Bug de dado | novo caso de ouro em `tests/golden/` |
| Convenção ignorada | `validate_naming.py` ou `check_contracts.py` |
| Agente fora do escopo | `tools` e instruções em `.claude/agents/<agente>.md` |

Registre em `docs/licoes-aprendidas.md`.

## Sinais de alerta

- Você está revisando sintaxe → o harness tem lacuna; adicione validador.
- Muitos escalonamentos → specs estão vagas; reforce o template.
- Custo subindo → adicione orçamento por tarefa no `orquestrador`.
- Gates viram carimbo → você está aprovando rápido demais; volte ao checklist.
