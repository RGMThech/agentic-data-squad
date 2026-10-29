# Operando a squad pelo Squad Console

O [Squad Console](https://github.com/RGMThech/agentic-squad-console) é a interface web desta squad: abre features, aciona agentes, aprova gates e mostra custos. Este repositório já vem preparado para ele.

## Peças deste repositório que o console usa

| Arquivo | Papel |
|---------|-------|
| `.squad/squad.yaml` | Nome, cliente, plataforma, modelo dos agentes, limite de turnos e alerta de custo |
| `.squad/members.yaml` | Quem é operador, membro ou leitor (logins do GitHub) |
| `.github/workflows/squad-agent.yml` | Executa um agente em modo não interativo quando o console pede |
| `scripts/squad_run.py` | Valida o pedido, roda o Claude Code como o agente e registra custo e turnos |
| `.github/workflows/squad-gates.yml` | Checagens do harness; também é disparado após cada execução |

## O que acontece quando o console aciona um agente

1. **Disparo.** O console chama o workflow `squad-agent` com `agente`, `feature` e `instrucao`.
2. **Validação.** `squad_run.py validar` confere três coisas:
   - o agente existe em `.claude/agents/`
   - a feature segue o padrão `NNN-slug`
   - quem acionou é operador ou membro em `.squad/members.yaml`
3. **Branch.** O workflow troca para a branch `squad/<feature>`, ou cria se ela não existir.
4. **Execução.** O Claude Code roda com:
   - o prompt do agente anexado ao system prompt
   - só as ferramentas listadas no `tools:` do agente
   - o modelo e o limite de turnos de `.squad/squad.yaml`
5. **Validadores.** O workflow roda os validadores do harness, commita, faz push e cria o PR em rascunho (se ainda não existir).
6. **Registro.** Um comentário no PR registra a execução:
   - custo em US$, turnos e duração
   - resultado dos validadores
   - resumo do agente
   O console lê esses comentários para montar os relatórios de custo.
7. **Checagens.** O workflow `squad-gates` é disparado na branch para que as checagens apareçam no PR.

## Gates pelo console

- **G1 e G2:** o console grava `status: aprovado`, `aprovado_por` e `aprovado_em` no front matter da spec ou do design, na branch da feature. O `check_spec.py` confere se `aprovado_por` é um operador.
- **G3:** o console marca o PR como pronto, registra a aprovação do operador e faz o merge (squash).

## Configuração necessária no GitHub

- **Segredo:** `ANTHROPIC_API_KEY` nos segredos do GitHub Actions do repositório. Pode ser cadastrado pelo console, em **Configuração → Chave da API**.
- **Permissão do Actions:** na organização (ou no repositório), em **Settings → Actions → General → Workflow permissions**:
  - marque **Read and write permissions**
  - marque **Allow GitHub Actions to create and approve pull requests**

  Sem isso, o workflow não consegue abrir o PR da feature.
