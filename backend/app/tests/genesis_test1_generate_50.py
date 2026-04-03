import asyncio
import json
import os
import sys
import re
from datetime import datetime
import httpx

# ─── FIX CRÍTICO PARA WINDOWS ────────────────────────────────────────────────
# O ProactorEventLoop (default no Win 3.10+) quebra o httpx.
# Deve ser definido ANTES de qualquer import de loop de eventos.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_URL     = "http://localhost:11434/api/chat"
DEFAULT_MODEL  = "qwen2.5:7b"
NUM_CTX        = 16384
MAX_RETRIES    = 3
RETRY_DELAY_S  = 5

PROMPTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genesis_prompts_variants.json")
SPEC_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genesis_benchmark_spec.json")
OUTPUT_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genesis_souls_50_master.json")
LOG_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genesis_failures.log")

# ─── Injeção de schema no system_prompt de cada variant ─────────────────────
# Garante que TODOS os variants peçam JSON com estrutura padronizada,
# independente do que estiver no arquivo de prompts.
JSON_SCHEMA_INJECTION = """

INSTRUÇÃO OBRIGATÓRIA DE FORMATO — SOBREPÕE QUALQUER OUTRA:
Retorne EXCLUSIVAMENTE um objeto JSON válido, sem texto antes ou depois, sem blocos markdown.
A estrutura obrigatória é:
{
  "name": "<nome do autor>",
  "variant": "<id da variante>",
  "system_prompt": "<o prompt de sistema completo gerado, mínimo 300 palavras>"
}
Não inclua nenhuma chave adicional fora desse schema.
"""

# ─── Extração de JSON robusta ─────────────────────────────────────────────────
def extract_json_hardened(text: str) -> tuple[dict | None, str]:
    """
    Tenta extrair JSON do texto retornado pelo modelo.
    Retorna (dict, reason) onde reason explica o que aconteceu.
    """
    if not text or not text.strip():
        return None, "resposta vazia"

    # 1. Tenta parse direto (modelo perfeito)
    try:
        return json.loads(text.strip()), "parse_direto"
    except json.JSONDecodeError:
        pass

    # 2. Remove blocos markdown ```json ... ``` ou ``` ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```", "", cleaned)
    try:
        return json.loads(cleaned.strip()), "markdown_removido"
    except json.JSONDecodeError:
        pass

    # 3. Extrai o maior bloco { ... } usando stack de delimitadores
    #    (mais confiável que regex greedy para JSON aninhado)
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate), "stack_extraction"
                    except json.JSONDecodeError as e:
                        # Tenta corrigir aspas simples comuns
                        try:
                            fixed = candidate.replace("'", '"')
                            return json.loads(fixed), "stack_single_quote_fix"
                        except Exception:
                            return None, f"stack_found_but_invalid: {e}"
                    break

    return None, "nenhum_json_encontrado"


def _log_failure(variant_id: str, author_name: str, reason: str, raw: str):
    """Grava falhas em arquivo de log para diagnóstico posterior."""
    with open(LOG_PATH, "a", encoding="utf-8") as lf:
        lf.write(f"\n{'─'*80}\n")
        lf.write(f"[{datetime.now().isoformat()}] VARIANT={variant_id} | AUTHOR={author_name}\n")
        lf.write(f"MOTIVO: {reason}\n")
        lf.write(f"RAW (primeiros 800 chars):\n{raw[:800]}\n")


async def _check_ollama_alive() -> bool:
    """Verifica se o Ollama está respondendo antes de iniciar o benchmark."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            return r.status_code == 200
    except Exception as e:
        print(f"[PRE-CHECK] Ollama não respondeu: {e}")
        return False


async def generate_ollama(
    system_prompt: str,
    user_prompt: str,
    variant_id: str,
    author_name: str
) -> tuple[dict | None, str]:
    """
    Chama o Ollama com retry automático.
    Retorna (parsed_dict, raw_text).
    """
    # Injeta o schema em TODOS os system prompts para uniformizar output
    enriched_system = system_prompt + JSON_SCHEMA_INJECTION

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": enriched_system},
            {"role": "user",   "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "num_ctx":     NUM_CTX,
            "temperature": 0.7,
        }
    }

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(900.0)) as client:
                response = await client.post(OLLAMA_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_content = data.get("message", {}).get("content", "")

                parsed, reason = extract_json_hardened(raw_content)

                if parsed is None:
                    _log_failure(variant_id, author_name, reason, raw_content)
                    print(f"\n  ⚠ Tentativa {attempt}/{MAX_RETRIES}: JSON inválido ({reason})")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY_S)
                    continue

                return parsed, raw_content

        except httpx.TimeoutException:
            last_error = "timeout"
            print(f"\n  ⚠ Tentativa {attempt}/{MAX_RETRIES}: Timeout (modelo lento?)")
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}"
            print(f"\n  ⚠ Tentativa {attempt}/{MAX_RETRIES}: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f"\n  ⚠ Tentativa {attempt}/{MAX_RETRIES}: {last_error}")

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY_S)

    _log_failure(variant_id, author_name, f"max_retries_esgotados: {last_error}", "")
    return None, last_error


async def run_test1():
    # ── Pré-checks ──────────────────────────────────────────────────────────
    print("🔍 Verificando Ollama...", end=" ", flush=True)
    if not await _check_ollama_alive():
        print("\n❌ Ollama não está rodando em localhost:11434. Inicie com: ollama serve")
        sys.exit(1)
    print("OK")

    # ── Carrega inputs ───────────────────────────────────────────────────────
    for path, label in [(PROMPTS_PATH, "prompts"), (SPEC_PATH, "spec")]:
        if not os.path.exists(path):
            print(f"❌ Arquivo não encontrado: {path} ({label})")
            sys.exit(1)

    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    variants = prompts_data["variants"]
    authors  = spec_data["authors"]

    # ── Carrega progresso anterior ───────────────────────────────────────────
    master_data: dict = {}
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                master_data = json.load(f)
            print(f"↩ Progresso anterior carregado de: {OUTPUT_PATH}")
        except json.JSONDecodeError:
            print("⚠ Output anterior corrompido — iniciando do zero.")

    total   = len(variants) * len(authors)
    current = 0
    skipped = 0
    failed  = 0
    success = 0

    print(f"\n🧬 [GENESIS BENCHMARK] {len(variants)} variantes × {len(authors)} autores = {total} gerações")
    print(f"   Modelo: {DEFAULT_MODEL} | CTX: {NUM_CTX} | Retries: {MAX_RETRIES}\n")

    for v in variants:
        v_id = v["id"]
        master_data.setdefault(v_id, {})

        for author in authors:
            current += 1
            a_name = author["name"]
            prefix = f"[{current:>3}/{total}]"

            # Skip se já existe
            if a_name in master_data[v_id]:
                print(f"{prefix} ⏭ SKIP  {a_name:<20} via {v_id}")
                skipped += 1
                continue

            print(f"{prefix} 🧬 {a_name:<20} via {v_id} ...", end="", flush=True)

            parsed, raw = await generate_ollama(
                system_prompt=v["content"],
                user_prompt=author["bio_prompt"],
                variant_id=v_id,
                author_name=a_name,
            )

            if parsed is None:
                print(f" ❌ FAIL (ver {os.path.basename(LOG_PATH)})")
                failed += 1
                continue

            # Extrai o system_prompt de forma agnóstica ao schema
            sys_content = (
                parsed.get("system_prompt")
                or parsed.get("autor", {}).get("system_prompt")
                or json.dumps(parsed, ensure_ascii=False)
            )
            word_count = len(sys_content.split())

            master_data[v_id][a_name] = {
                "author":        a_name,
                "variant":       v_id,
                "system_prompt": sys_content,
                "raw_response":  parsed,
                "metrics": {
                    "word_count": word_count,
                    "timestamp":  datetime.now().isoformat(),
                }
            }

            # Salva incrementalmente (seguro contra interrupções)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(master_data, f, indent=2, ensure_ascii=False)

            print(f" ✅ {word_count} palavras")
            success += 1

    # ── Resumo final ─────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"✅ Concluído  │ OK: {success} │ Skip: {skipped} │ Falhas: {failed}")
    print(f"📄 Output    → {OUTPUT_PATH}")
    if failed:
        print(f"📋 Log erros → {LOG_PATH}")
    print(f"{'═'*60}")


if __name__ == "__main__":
    try:
        asyncio.run(run_test1())
    except KeyboardInterrupt:
        print("\n⛔ Abortado pelo usuário. Progresso foi salvo.")