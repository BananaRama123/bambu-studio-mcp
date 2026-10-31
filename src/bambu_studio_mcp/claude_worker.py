"""Anthropic Claude Sub-Agent Worker Client.

Allows the Lead Agent (or MCP caller) to delegate coding, analysis, and file-generation tasks
directly to Anthropic's Messages API (`https://api.anthropic.com/v1/messages`) using the local `.env` key.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _find_claude_cli() -> Optional[str]:
    """Locate the `claude` CLI executable (powered by the user's Claude Max subscription)."""
    found = shutil.which("claude") or shutil.which("claude.cmd") or shutil.which("claude.exe")
    if found:
        return found
    home = Path.home()
    candidates = [
        home / ".claude" / "local" / "claude.exe",
        home / ".local" / "bin" / "claude.exe",
        home / "AppData" / "Local" / "Programs" / "claude" / "claude.exe",
        home / "AppData" / "Roaming" / "npm" / "claude.cmd",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _load_env_file() -> Dict[str, str]:
    """Load key=value pairs from the workspace `.env` file without external dependencies."""
    env_vars: Dict[str, str] = {}
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def get_latest_opus_model(api_key: str) -> Tuple[str, List[str]]:
    """Query https://api.anthropic.com/v1/models to discover all available models and pick the latest Opus."""
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
            opus_models = [m for m in models if "opus" in m.lower()]
            if opus_models:
                return opus_models[0], models
            if models:
                return models[0], models
    except Exception:
        pass
    return "claude-opus-4-20250514", []


def delegate_to_claude(
    task_prompt: str,
    context_files: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """Send a task to Claude via Anthropic's API, optionally attaching workspace files as context."""
    env_file = _load_env_file()
    api_key = os.environ.get("ANTHROPIC_API_KEY") or env_file.get("ANTHROPIC_API_KEY", "")
    has_api_key = bool(api_key and api_key != "paste_your_sk_ant_key_here")
    best_opus, available_models = get_latest_opus_model(api_key) if has_api_key else ("claude-opus-4-20250514", [])
    env_model = env_file.get("CLAUDE_MODEL", "")
    if not model:
        if not env_model or "sonnet" in env_model.lower():
            chosen_model = best_opus
        else:
            chosen_model = env_model
    else:
        chosen_model = model

    context_blocks: List[str] = []
    if context_files:
        for fp in context_files:
            p = Path(fp)
            if p.exists() and p.is_file():
                content = p.read_text(encoding="utf-8", errors="ignore")
                context_blocks.append(f"--- FILE: {p.name} ({p}) ---\n{content}\n--- END FILE ---")

    full_user_message = task_prompt
    if context_blocks:
        full_user_message = "\n\n".join(context_blocks) + "\n\nTASK:\n" + task_prompt

    # 1. Prefer the `claude` CLI (which bills against the user's flat-rate Claude Max subscription at $0 API cost!)
    claude_bin = _find_claude_cli()
    if claude_bin:
        try:
            clean_env = dict(os.environ)
            clean_env.pop("ANTHROPIC_API_KEY", None)
            workspace_root = str(Path(__file__).resolve().parent.parent.parent)
            system_brief = (
                "You are Claude Opus 5.5 acting as the specialized Sub-Agent on the `bambu-studio-mcp` repository "
                f"located at `{workspace_root}`. The Lead Agent (Gemini in Antigravity) delegates tasks to you. "
                "Follow file ownership boundaries strictly and return concise, high-signal summaries."
            )
            proc = subprocess.run(
                [
                    claude_bin,
                    "-p",
                    "--model",
                    "opus",
                    "--append-system-prompt",
                    system_brief,
                    "--allowedTools",
                    "Read,Edit,Write,Grep,Glob",
                ],
                input=full_user_message,
                cwd=workspace_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=clean_env,
                timeout=180.0,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                reply_text = proc.stdout.strip()
                saved_to = None
                if output_file and reply_text:
                    out_p = Path(output_file)
                    out_p.parent.mkdir(parents=True, exist_ok=True)
                    out_p.write_text(reply_text, encoding="utf-8")
                    saved_to = str(out_p)
                return {
                    "success": True,
                    "billing_mode": "Claude Max Subscription (Opus 5.5 via claude CLI - $0 API cost)",
                    "model": "Opus 5.5 (Claude Max)",
                    "saved_to_file": saved_to,
                    "claude_response": reply_text,
                }
            return {
                "success": False,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if not api_key or api_key == "paste_your_sk_ant_key_here":
        return {
            "success": False,
            "error": (
                "Claude Code CLI (`claude`) not found yet. Run `irm https://claude.ai/install.ps1 | iex` "
                "and `claude login` in PowerShell to use your Claude Max subscription at $0 API cost."
            ),
        }

    payload = json.dumps({
        "model": chosen_model,
        "max_tokens": max_tokens,
        "system": (
            "You are a senior Python and 3D printing systems engineer working as a specialized "
            "sub-agent on the bambu-studio-mcp repository. Return clean, production-ready code or analysis."
        ),
        "messages": [
            {"role": "user", "content": full_user_message},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        return {
            "success": False,
            "status_code": exc.code,
            "error": err_body,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }

    text_blocks = [
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    ]
    reply_text = "\n".join(text_blocks).strip()

    saved_to = None
    if output_file and reply_text:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(reply_text, encoding="utf-8")
        saved_to = str(out_p)

    return {
        "success": True,
        "model": data.get("model", chosen_model),
        "available_opus_and_other_models": available_models[:10],
        "usage": data.get("usage", {}),
        "saved_to_file": saved_to,
        "claude_response": reply_text,
    }
