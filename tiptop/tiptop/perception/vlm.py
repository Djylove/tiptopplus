import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import tomllib
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from tiptop.config import tiptop_cfg

_log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.toml"
_CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
_DEFAULT_GEMINI_MODEL = "gemini-robotics-er-1.5-preview"
_DEFAULT_OPENAI_MODEL = "gpt-5-codex"
_DEFAULT_CODEX_MODEL = "gpt-5.4"
_SUPPORTED_PROVIDERS = {"gemini", "openai", "codex"}
_EMITTED_WARNINGS: set[str] = set()

_DETECT_AND_TRANSLATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "bboxes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "label": {"type": "string"},
                },
                "required": ["box_2d", "label"],
                "additionalProperties": False,
            },
        },
        "predicates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "args"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["bboxes", "predicates"],
    "additionalProperties": False,
}

_GRIPPER_DETECTION_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "box_2d": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 4,
                "maxItems": 4,
            },
            "label": {"type": "string"},
        },
        "required": ["box_2d", "label"],
        "additionalProperties": False,
    },
}


@cache
def load_prompt(prompt_name: str) -> str:
    """Load a prompt template from the prompts directory."""
    return (_PROMPTS_DIR / f"{prompt_name}.txt").read_text().strip()


@cache
def _load_codex_config() -> dict[str, Any]:
    if not _CODEX_CONFIG_PATH.exists():
        return {}
    try:
        with _CODEX_CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    except Exception as exc:
        _log.warning(f"Failed to parse {_CODEX_CONFIG_PATH}: {exc}")
        return {}


def load_json(response_text: str) -> list | dict:
    """Extract JSON string from code fencing if present."""
    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.replace("```json", "").replace("```", "")
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.replace("```", "")

    try:
        return _decode_json_with_recovery(cleaned_text)
    except json.decoder.JSONDecodeError:
        _log.error(f"Invalid JSON: {cleaned_text}")
        raise


def _decode_json_with_recovery(cleaned_text: str) -> list | dict:
    """Decode JSON from a raw model response, recovering from leading/trailing text when possible."""
    try:
        return json.loads(cleaned_text)
    except json.decoder.JSONDecodeError:
        decoder = json.JSONDecoder()
        for idx, char in enumerate(cleaned_text):
            if char not in "[{":
                continue
            try:
                results, _ = decoder.raw_decode(cleaned_text[idx:])
                _log.warning("Recovered structured JSON from a response that contained extra text.")
                return results
            except json.decoder.JSONDecodeError:
                continue
        raise


def _parse_response(response_text: str) -> tuple[list, list]:
    """Parse VLM response text into bboxes and grounded atoms."""
    try:
        result = load_json(response_text)
    except Exception:
        raise ValueError(f"VLM returned a non-JSON response; check for a discrepancy in your image: {response_text}")
    bboxes = result.get("bboxes", [])
    grounded_atoms = [
        {"predicate": spec["name"], "args": spec["args"]}
        for spec in result.get("predicates", [])
        if spec.get("name") and spec.get("args")
    ]
    return bboxes, grounded_atoms


def _cfg_value(path: str, default: str | None = None) -> str | None:
    """Read a string value from the TiPToP config if present."""
    try:
        node: Any = tiptop_cfg()
        for part in path.split("."):
            if part not in node:
                return default
            node = node[part]
        if node in (None, ""):
            return default
        return str(node)
    except Exception:
        return default


def _codex_cfg_value(path: str, default: str | None = None) -> str | None:
    try:
        node: Any = _load_codex_config()
        for part in path.split("."):
            if part not in node:
                return default
            node = node[part]
        if node in (None, ""):
            return default
        return str(node)
    except Exception:
        return default


def _warn_once(message: str) -> None:
    if message in _EMITTED_WARNINGS:
        return
    _EMITTED_WARNINGS.add(message)
    _log.warning(message)


def _find_codex_cli() -> str | None:
    configured_path = os.getenv("TIPTOP_CODEX_EXECUTABLE")
    if configured_path:
        expanded_path = str(Path(configured_path).expanduser())
        if Path(expanded_path).exists():
            return expanded_path
        return shutil.which(configured_path) or shutil.which(expanded_path)
    return shutil.which("codex")


def _has_logged_in_codex() -> bool:
    if not _CODEX_AUTH_PATH.exists():
        return False
    try:
        return bool(_CODEX_AUTH_PATH.read_text(encoding="utf-8").strip())
    except OSError:
        return False


def vlm_provider() -> Literal["gemini", "openai", "codex"]:
    provider_env = os.getenv("TIPTOP_VLM_PROVIDER")
    provider = (provider_env or _cfg_value("perception.vlm.provider") or "gemini").strip().lower()
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported TIPTOP_VLM_PROVIDER='{provider}'. Expected one of: {sorted(_SUPPORTED_PROVIDERS)}"
        )
    if provider_env or provider != "gemini" or os.getenv("GOOGLE_API_KEY"):
        return provider  # type: ignore[return-value]
    if _find_codex_cli() and _has_logged_in_codex():
        _warn_once(
            "GOOGLE_API_KEY is not set and TiPToP is configured for Gemini by default; "
            "falling back to the logged-in local Codex CLI. "
            "Set TIPTOP_VLM_PROVIDER explicitly if you want to pin a provider."
        )
        return "codex"
    return provider  # type: ignore[return-value]


def vlm_model(provider: str | None = None) -> str:
    provider = provider or vlm_provider()
    if model_id := os.getenv("TIPTOP_VLM_MODEL"):
        return model_id
    if provider == "codex" and (model_id := os.getenv("TIPTOP_CODEX_MODEL")):
        return model_id
    if provider == "openai" and (model_id := os.getenv("TIPTOP_OPENAI_MODEL")):
        return model_id
    if provider == "gemini" and (model_id := os.getenv("TIPTOP_GEMINI_MODEL")):
        return model_id
    if model_id := _cfg_value("perception.vlm.model"):
        return model_id
    if provider == "codex" and (model_id := _codex_cfg_value("model")):
        return model_id
    if provider == "codex":
        return _DEFAULT_CODEX_MODEL
    if provider == "openai":
        return _DEFAULT_OPENAI_MODEL
    return _DEFAULT_GEMINI_MODEL


def vlm_description() -> str:
    provider = vlm_provider()
    model_id = vlm_model(provider)
    return f"{provider}:{model_id}"


def _require_api_key(env_var: str, provider: str) -> None:
    if os.getenv(env_var):
        return
    raise RuntimeError(
        f"{provider} VLM provider requires `{env_var}` to be set. "
        f"Current provider is `{provider}` (from TIPTOP_VLM_PROVIDER or perception.vlm.provider)."
    )


def _openai_client():
    _require_api_key("OPENAI_API_KEY", "openai")
    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenAI provider selected but the `openai` package is not installed in the TiPToP environment. "
            "Run `pixi install` from the repo root after updating dependencies."
        ) from exc
    return OpenAI()


def _gemini_client():
    _require_api_key("GOOGLE_API_KEY", "gemini")
    try:
        from google import genai
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Gemini provider selected but the `google-genai` package is not installed in the TiPToP environment."
        ) from exc
    return genai.Client()


def _require_codex_cli() -> str:
    codex_executable = _find_codex_cli()
    if codex_executable:
        return codex_executable
    raise RuntimeError(
        "Codex provider selected but the `codex` CLI was not found on PATH. "
        "Install Codex CLI or set TIPTOP_CODEX_EXECUTABLE to its full path."
    )


def _image_to_data_url(image: Image.Image, image_format: str = "PNG") -> str:
    buf = BytesIO()
    image.save(buf, format=image_format)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = f"image/{image_format.lower()}"
    return f"data:{mime};base64,{encoded}"


def _generate_text_with_gemini(image: Image.Image, prompt: str, model_id: str, temperature: float | None) -> str:
    from google.genai import types

    client = _gemini_client()
    response = client.models.generate_content(
        model=model_id,
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            temperature=temperature,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text


def _generate_text_with_openai(image: Image.Image, prompt: str, model_id: str, temperature: float | None) -> str:
    client = _openai_client()
    image_url = _image_to_data_url(image)
    request: dict[str, Any] = {
        "model": model_id,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_url},
                ],
            }
        ],
    }
    if temperature is not None:
        request["temperature"] = temperature
    response = client.responses.create(**request)
    return response.output_text


def _generate_text_with_codex(
    image: Image.Image,
    prompt: str,
    model_id: str,
    temperature: float | None,
    json_schema: dict[str, Any] | None,
) -> str:
    del temperature  # Codex CLI does not currently expose a per-call temperature flag here.

    if json_schema is None:
        raise RuntimeError("Codex VLM provider requires an explicit JSON schema for reliable structured output.")

    codex_executable = _require_codex_cli()
    reasoning_effort = (
        os.getenv("TIPTOP_CODEX_REASONING_EFFORT")
        or _cfg_value("perception.vlm.reasoning_effort")
        or _codex_cfg_value("model_reasoning_effort")
        or "low"
    )
    timeout_sec = int(os.getenv("TIPTOP_CODEX_TIMEOUT_SEC", "300"))
    max_attempts = max(1, int(os.getenv("TIPTOP_CODEX_MAX_ATTEMPTS", "3")))

    with tempfile.TemporaryDirectory(prefix="tiptop-codex-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        image_path = tmpdir_path / "image.png"
        schema_path = tmpdir_path / "schema.json"
        output_path = tmpdir_path / "output.json"

        image.save(image_path, format="PNG")
        schema_path.write_text(json.dumps(json_schema), encoding="utf-8")

        _log.info(f"Running local Codex CLI with model {model_id!r} and reasoning effort {reasoning_effort!r}")
        last_error: str | None = None
        for attempt in range(1, max_attempts + 1):
            if output_path.exists():
                output_path.unlink()

            attempt_prompt = prompt
            if attempt > 1:
                attempt_prompt = (
                    f"{prompt}\n\n"
                    "Return only valid JSON that strictly matches the provided schema. "
                    "Do not output markdown, code fences, or prose."
                )

            cmd = [
                codex_executable,
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--ephemeral",
                "-m",
                model_id,
                "-c",
                'model_provider="codex"',
                "-c",
                f'model_reasoning_effort="{reasoning_effort}"',
                "--image",
                str(image_path),
                "--output-schema",
                str(schema_path),
                "-o",
                str(output_path),
                attempt_prompt,
            ]
            try:
                completed = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
            except subprocess.TimeoutExpired as exc:
                last_error = f"Local Codex CLI call timed out after {timeout_sec} seconds"
                if attempt == max_attempts:
                    raise RuntimeError(last_error) from exc
                _log.warning(f"{last_error}; retrying ({attempt}/{max_attempts})")
                continue

            stderr = completed.stderr.strip() if completed.stderr else ""
            stdout = completed.stdout.strip() if completed.stdout else ""
            output_text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            candidate_sources = [("output file", output_text), ("stdout", stdout)]

            for source_name, candidate in candidate_sources:
                if not candidate:
                    continue
                try:
                    parsed = _decode_json_with_recovery(candidate)
                    # Return canonical JSON text so downstream load_json parsing is stable.
                    return json.dumps(parsed)
                except json.decoder.JSONDecodeError:
                    last_error = f"{source_name} was not valid JSON"

            if completed.returncode == 0:
                last_error = (
                    last_error
                    or stderr
                    or stdout
                    or "Local Codex CLI produced an empty or non-JSON response"
                )
            else:
                last_error = stderr or stdout or "Local Codex CLI call failed without stdout/stderr"

            if attempt < max_attempts:
                _log.warning(
                    "Local Codex CLI attempt %d/%d did not yield structured output: %s",
                    attempt,
                    max_attempts,
                    last_error,
                )
                continue

            if completed.returncode != 0:
                raise RuntimeError(f"Local Codex CLI call failed: {last_error}")
            raise RuntimeError(f"Local Codex CLI returned no structured output: {last_error}")

        raise RuntimeError(last_error or "Local Codex CLI failed without an error message.")


def detect_json_with_prompt(
    image: Image.Image,
    prompt: str,
    model_id: str | None = None,
    temperature: float | None = None,
    json_schema: dict[str, Any] | None = None,
) -> list | dict:
    """Run the configured VLM with a raw prompt and parse the returned JSON."""
    provider = vlm_provider()
    model_id = model_id or vlm_model(provider)
    _log.info(f"Using VLM provider {provider!r} with model {model_id!r}")
    if provider == "codex":
        response_text = _generate_text_with_codex(image, prompt, model_id, temperature, json_schema)
    elif provider == "openai":
        response_text = _generate_text_with_openai(image, prompt, model_id, temperature)
    else:
        response_text = _generate_text_with_gemini(image, prompt, model_id, temperature)
    return load_json(response_text)


def detect_and_translate(
    image: Image.Image,
    task_instruction: str,
    model_id: str | None = None,
    temperature: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Detect objects and translate the task using the configured VLM provider."""
    prompt = load_prompt("detect_and_translate").format(task_instruction=task_instruction)
    response = detect_json_with_prompt(
        image=image,
        prompt=prompt,
        model_id=model_id,
        temperature=temperature,
        json_schema=_DETECT_AND_TRANSLATE_SCHEMA,
    )
    response_text = json.dumps(response)
    return _parse_response(response_text)


async def detect_and_translate_async(
    image: Image.Image,
    task_instruction: str,
    model_id: str | None = None,
    temperature: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Asynchronously detect objects and translate the task using the configured VLM provider."""
    return await asyncio.to_thread(
        detect_and_translate,
        image,
        task_instruction,
        model_id,
        temperature,
    )
