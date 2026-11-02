---
name: seguranca-app
description: Checklist de segurança de aplicações (OWASP Top 10, segredos, dependências, LGPD). Use ao desenhar, implementar, testar ou revisar código.
---

# Segurança de aplicações

## Checklist
- **Entrada:** valide tipo, tamanho e formato no servidor; nunca confie no cliente.
- **Injeção:** consultas parametrizadas; nada de concatenar SQL, comandos de shell ou HTML com entrada do usuário.
- **Autenticação e sessão:** use a biblioteca do projeto; cookies `HttpOnly`, `Secure`, `SameSite`.
- **Autorização:** verifique em cada rota se o usuário pode acessar aquele recurso (não só se está logado).
- **Segredos:** só em variável de ambiente ou cofre. `scripts/check_software.py` bloqueia chaves privadas, tokens e senhas no código.
- **Dependências:** versões fixadas; não adicione pacote abandonado ou com vulnerabilidade conhecida.
- **Erros:** mensagem genérica ao usuário, detalhe só no log; logs sem senha, token ou dado pessoal.
- **Arquivos:** valide tipo e tamanho de upload; nunca use o nome enviado pelo usuário como caminho.

## LGPD
- Colete só o necessário para a finalidade da spec.
- Dados pessoais mascarados em logs e telas administrativas quando possível.
- Exclusão e exportação de dados do titular: se a feature cria dado pessoal, o design diz como atender.
