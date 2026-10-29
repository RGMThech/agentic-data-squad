#!/usr/bin/env python3
"""Executa um agente da squad em modo não interativo (usado pelo workflow squad-agent).

Subcomandos:
    validar     valida agente, feature e permissão de quem acionou
    executar    roda o Claude Code como o agente e grava o registro da execução
    comentario  gera o corpo do comentário do PR com o registro da execução

Todas as entradas vêm de variáveis de ambiente (nunca interpoladas em shell):
    AGENTE, FEATURE, INSTRUCAO, ATOR, RUN_URL, RUN_ID, REGISTRO (caminho do JSON)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RE_FEATURE = re.compile(r"^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
MARCADOR = "squad-run"


def _yaml(caminho: Path) -> dict:
    import yaml

    if not caminho.exists():
        return {}
    return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}


def _frontmatter(texto: str) -> tuple[dict, str]:
    import yaml

    if not texto.startswith("---"):
        return {}, texto
    _, fm, corpo = texto.split("---", 2)
    return yaml.safe_load(fm) or {}, corpo.strip()


def _falhar(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)


def _norm(v: str) -> str:
    return str(v or "").strip().lstrip("@").lower()


def quem_acionou() -> str:
    """Identidade validada de quem pediu a execução.

    - Disparo pelo Squad Console: o ator do GitHub é o bot do GitHub App
      (`console_bot` em .squad/squad.yaml); quem pediu vem em SOLICITANTE (e-mail).
    - Disparo manual na aba Actions: vale o login de quem disparou; SOLICITANTE é ignorado.
    """
    ator = _norm(os.environ.get("ATOR", ""))
    bot = _norm(_yaml(ROOT / ".squad" / "squad.yaml").get("console_bot", ""))
    if bot and ator == bot:
        solicitante = _norm(os.environ.get("SOLICITANTE", ""))
        if not solicitante:
            _falhar("Execução do console sem solicitante.")
        return solicitante
    return ator


def validar() -> None:
    agente, feature = os.environ["AGENTE"], os.environ["FEATURE"]
    if not re.fullmatch(r"[a-z][a-z-]+", agente) or not (ROOT / ".claude" / "agents" / f"{agente}.md").exists():
        _falhar(f"Agente desconhecido: {agente}")
    if not RE_FEATURE.match(feature):
        _falhar(f"Feature inválida: {feature} (use NNN-slug)")
    quem = quem_acionou()
    membros = _yaml(ROOT / ".squad" / "members.yaml")
    autorizados = {_norm(x) for x in (membros.get("operadores") or []) + (membros.get("membros") or [])}
    if autorizados and quem not in autorizados:
        _falhar(f"{quem} não é operador nem membro desta squad (.squad/members.yaml)")
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f"QUEM={quem}\n")
    print(f"ok: {agente} · {feature} · {quem}")


def _prompt(agente: str, feature: str, instrucao: str, ator: str) -> str:
    return f"""Você está executando como o agente `{agente}` da squad, de forma não interativa (GitHub Actions).

Feature: specs/{feature}/   (branch atual: squad/{feature})
Acionado por: {ator}.

## Instrução
{instrucao}

## Regras desta execução
- Siga o AGENTS.md e as instruções do seu papel (já anexadas ao seu system prompt).
- Não faça git commit, push, merge nem abra PR: o workflow cuida disso.
- Não há humano disponível para perguntas agora. Se precisar de decisão do Operador,
  registre no artefato (por exemplo, em "Dúvidas abertas" da spec) e encerre.
- Antes de terminar, rode: python scripts/validate_naming.py && python scripts/check_contracts.py && python scripts/check_spec.py
- Termine com um resumo de no máximo 8 linhas: o que fez, arquivos alterados e decisões pendentes para o Operador.
"""


def _ler_resultado(stdout: str) -> dict:
    """Extrai o objeto final do `claude --output-format json` (saída inteira ou última linha)."""
    texto = stdout.strip()
    if not texto:
        return {}
    candidatos = [texto] + texto.splitlines()[::-1]
    for c in candidatos:
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, list):  # alguns formatos devolvem a lista de eventos
            obj = next((e for e in reversed(obj) if isinstance(e, dict) and e.get("type") == "result"), {})
        if isinstance(obj, dict):
            return obj
    return {}


def executar() -> None:
    agente, feature = os.environ["AGENTE"], os.environ["FEATURE"]
    instrucao = os.environ.get("INSTRUCAO", "").strip()
    ator = os.environ.get("QUEM") or os.environ["ATOR"]
    registro_path = Path(os.environ["REGISTRO"])
    squad = _yaml(ROOT / ".squad" / "squad.yaml")

    meta, corpo = _frontmatter((ROOT / ".claude" / "agents" / f"{agente}.md").read_text(encoding="utf-8"))
    ferramentas = [t.strip() for t in str(meta.get("tools", "Read,Grep,Glob")).split(",") if t.strip()]
    modelo = str(squad.get("modelo", "sonnet"))
    max_turnos = str(squad.get("max_turnos", 60))

    cmd = [
        "claude", "-p", _prompt(agente, feature, instrucao, ator),
        "--output-format", "json",
        "--model", modelo,
        "--max-turns", max_turnos,
        "--permission-mode", "acceptEdits",
        "--allowedTools", ",".join(ferramentas),
        "--append-system-prompt", corpo,
    ]
    inicio = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    duracao_ms = int((time.time() - inicio) * 1000)

    saida = _ler_resultado(proc.stdout)

    erro = proc.returncode != 0 or bool(saida.get("is_error"))
    registro = {
        "run_id": os.environ.get("RUN_ID"),
        "run_url": os.environ.get("RUN_URL"),
        "agente": agente,
        "feature": feature,
        "ator": ator,
        "modelo": modelo,
        "status": "falha" if erro else "sucesso",
        "custo_usd": round(float(saida.get("total_cost_usd") or 0), 4),
        "turnos": saida.get("num_turns"),
        "duracao_ms": saida.get("duration_ms") or duracao_ms,
        "resumo": (saida.get("result") or proc.stderr[-2000:] or "").strip()[:3000],
        "ts": int(time.time()),
    }
    registro_path.write_text(json.dumps(registro, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in registro.items() if k != "resumo"}, ensure_ascii=False))
    if erro:
        print(proc.stderr[-4000:], file=sys.stderr)
        sys.exit(1)


def comentario() -> None:
    reg = json.loads(Path(os.environ["REGISTRO"]).read_text(encoding="utf-8"))
    reg["validadores"] = os.environ.get("VALIDADORES", "desconhecido")
    minutos, segundos = divmod(int((reg.get("duracao_ms") or 0) / 1000), 60)
    icone = "✅" if reg["status"] == "sucesso" else "❌"
    resumo = "\n".join("> " + l for l in (reg.get("resumo") or "(sem resumo)").splitlines())
    meta = {k: v for k, v in reg.items() if k != "resumo"}
    print(f"<!-- {MARCADOR} {json.dumps(meta, ensure_ascii=False)} -->")
    print(f"### {icone} `{reg['agente']}` — {reg['status']}")
    print(
        f"**Acionado por:** {reg['ator']} · **Custo:** US$ {reg['custo_usd']:.2f} · "
        f"**Turnos:** {reg.get('turnos') or '-'} · **Duração:** {minutos}m{segundos:02d}s · "
        f"**Validadores:** {reg['validadores']} · [logs]({reg['run_url']})"
    )
    print()
    print(resumo)


if __name__ == "__main__":
    {"validar": validar, "executar": executar, "comentario": comentario}[sys.argv[1]]()
