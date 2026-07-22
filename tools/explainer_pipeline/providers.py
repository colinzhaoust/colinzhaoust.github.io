from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from .common import canonical_json, load_json, repo_path, sha256_json


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageResult:
    stage: str
    paper_id: str
    payload: dict[str, Any]
    provider: str
    model: str
    generation_mode: str
    response_sha256: str
    source_record: Optional[str] = None
    usage: Optional[dict[str, int]] = None
    duration_ms: int = 0


class StageProvider(Protocol):
    def generate(self, stage: str, paper_id: str, prompt: str) -> StageResult:
        ...


class ReplayProvider:
    """Replay reviewed JSON API outputs while preserving the production stage boundary."""

    def __init__(self, replay_root: Path) -> None:
        self.replay_root = replay_root

    def generate(self, stage: str, paper_id: str, prompt: str) -> StageResult:
        del prompt
        path = self.replay_root / paper_id / f"{stage}.json"
        try:
            record = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError(f"cannot load replay stage {paper_id}/{stage}: {exc}") from exc
        if record.get("schema_version") != "explainer-stage-replay/0.1.0":
            raise ProviderError(f"{path}: unsupported replay schema")
        if record.get("paper_id") != paper_id or record.get("stage") != stage:
            raise ProviderError(f"{path}: replay identity mismatch")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            raise ProviderError(f"{path}: replay payload must be an object")
        return StageResult(
            stage=stage,
            paper_id=paper_id,
            payload=payload,
            provider=str(record.get("provider", "reviewed_replay")),
            model=str(record.get("model", "reviewed_fixture")),
            generation_mode="frozen_replay",
            response_sha256=sha256_json(payload),
            source_record=repo_path(path),
            usage=None,
            duration_ms=0,
        )


class BedrockProvider:
    """Live JSON-only provider using the AWS Bedrock Converse CLI."""

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-5",
        region: str = "us-east-1",
        env_file: Optional[Path] = None,
        max_tokens: int = 7000,
    ) -> None:
        self.model_id = model_id
        self.region = region
        self.env_file = env_file
        self.max_tokens = max_tokens

    def _environment(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.env_file:
            for raw_line in self.env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip("'\"")
        if not env.get("AWS_BEARER_TOKEN_BEDROCK"):
            raise ProviderError(
                "live Bedrock mode requires AWS_BEARER_TOKEN_BEDROCK in the environment or --env-file"
            )
        env["AWS_EC2_METADATA_DISABLED"] = "true"
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
            env.pop(name, None)
        return env

    def generate(self, stage: str, paper_id: str, prompt: str) -> StageResult:
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        command = [
            "aws",
            "bedrock-runtime",
            "converse",
            "--region",
            self.region,
            "--model-id",
            self.model_id,
            "--messages",
            canonical_json(messages),
            "--inference-config",
            canonical_json({"maxTokens": self.max_tokens, "temperature": 0.2}),
            "--output", "json",
        ]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                check=True,
                env=self._environment(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise ProviderError(f"Bedrock stage {stage} failed: {detail.strip()}") from exc
        duration_ms = round((time.monotonic() - started) * 1000)
        try:
            response = json.loads(completed.stdout)
            raw = response["output"]["message"]["content"][0]["text"].strip()
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Bedrock stage {stage} returned an invalid Converse response") from exc
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Bedrock stage {stage} returned non-JSON output") from exc
        if not isinstance(payload, dict):
            raise ProviderError(f"Bedrock stage {stage} must return a JSON object")
        return StageResult(
            stage=stage,
            paper_id=paper_id,
            payload=payload,
            provider="amazon_bedrock",
            model=self.model_id,
            generation_mode="live",
            response_sha256=sha256_json(payload),
            usage=_bedrock_usage(response.get("usage", {})),
            duration_ms=duration_ms,
        )


class OpenAICompatibleProvider:
    """JSON-only adapter for WInE and Bedrock Mantle style HTTP endpoints."""

    def __init__(
        self,
        *,
        model_id: str,
        base_url: str,
        api_key_env: str = "OPENAI_API_KEY",
        env_file: Optional[Path] = None,
        api_path: str = "chat/completions",
        provider_name: str = "openai_compatible",
        max_tokens: int = 7000,
        timeout: int = 180,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.env_file = env_file
        self.api_path = api_path.strip("/")
        self.provider_name = provider_name
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _api_key(self) -> str:
        values = os.environ.copy()
        if self.env_file:
            for raw_line in self.env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("'\"")
        key = values.get(self.api_key_env, "")
        if not key:
            raise ProviderError(
                f"{self.provider_name} requires {self.api_key_env} in the environment or --env-file"
            )
        return key

    def _request_payload(self, prompt: str) -> dict[str, Any]:
        if self.api_path.endswith("responses"):
            return {
                "model": self.model_id,
                "input": prompt,
                "max_output_tokens": self.max_tokens,
            }
        return {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
        }

    def _response_text(self, response: dict[str, Any]) -> str:
        if self.api_path.endswith("responses"):
            if isinstance(response.get("output_text"), str):
                return response["output_text"]
            parts = []
            for item in response.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                        parts.append(content["text"])
            if parts:
                return "".join(parts)
            raise ProviderError(f"{self.provider_name} response contains no output text")
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.provider_name} response contains no chat completion text") from exc
        if not isinstance(content, str):
            raise ProviderError(f"{self.provider_name} chat completion content must be text")
        return content

    def generate(self, stage: str, paper_id: str, prompt: str) -> StageResult:
        request = urllib.request.Request(
            f"{self.base_url}/{self.api_path}",
            data=canonical_json(self._request_payload(prompt)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as opened:
                response = json.loads(opened.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderError(f"{self.provider_name} stage {stage} failed with HTTP {exc.code}: {detail}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.provider_name} stage {stage} request failed: {exc}") from exc
        duration_ms = round((time.monotonic() - started) * 1000)
        if not isinstance(response, dict):
            raise ProviderError(f"{self.provider_name} stage {stage} returned a non-object response")
        raw = self._response_text(response).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"{self.provider_name} stage {stage} returned non-JSON output") from exc
        if not isinstance(payload, dict):
            raise ProviderError(f"{self.provider_name} stage {stage} must return a JSON object")
        return StageResult(
            stage=stage,
            paper_id=paper_id,
            payload=payload,
            provider=self.provider_name,
            model=self.model_id,
            generation_mode="live",
            response_sha256=sha256_json(payload),
            usage=_openai_usage(response.get("usage", {})),
            duration_ms=duration_ms,
        )


def _bedrock_usage(raw: dict[str, Any]) -> dict[str, int]:
    input_tokens = int(raw.get("inputTokens", 0) or 0)
    output_tokens = int(raw.get("outputTokens", 0) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": 0,
        "total_tokens": int(raw.get("totalTokens", input_tokens + output_tokens) or 0),
    }


def _openai_usage(raw: dict[str, Any]) -> dict[str, int]:
    input_tokens = int(raw.get("input_tokens", raw.get("prompt_tokens", 0)) or 0)
    output_tokens = int(raw.get("output_tokens", raw.get("completion_tokens", 0)) or 0)
    details = raw.get("output_tokens_details", raw.get("completion_tokens_details", {})) or {}
    reasoning_tokens = int(details.get("reasoning_tokens", 0) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": int(raw.get("total_tokens", input_tokens + output_tokens) or 0),
    }


class VertexProvider:
    """Vertex Gemini adapter. Credential paths are consumed locally and never traced."""

    def __init__(
        self,
        *,
        model_id: str,
        credential_file: Path,
        project_id: str,
        location: str = "global",
        max_tokens: int = 7000,
        timeout: int = 180,
    ) -> None:
        self.model_id = model_id
        self.credential_file = credential_file
        self.project_id = project_id
        self.location = location
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _token(self) -> str:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
        except ImportError as exc:
            raise ProviderError("Vertex mode requires google-auth") from exc
        credentials = service_account.Credentials.from_service_account_file(
            self.credential_file,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        credentials.refresh(Request())
        return str(credentials.token)

    def generate(self, stage: str, paper_id: str, prompt: str) -> StageResult:
        host = "aiplatform.googleapis.com" if self.location == "global" else f"{self.location}-aiplatform.googleapis.com"
        url = (
            f"https://{host}/v1/projects/{self.project_id}/locations/{self.location}"
            f"/publishers/google/models/{self.model_id}:generateContent"
        )
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": self.max_tokens},
        }
        request = urllib.request.Request(
            url,
            data=canonical_json(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as opened:
                response = json.loads(opened.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderError(f"Vertex stage {stage} failed with HTTP {exc.code}: {detail}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Vertex stage {stage} request failed: {exc}") from exc
        duration_ms = round((time.monotonic() - started) * 1000)
        try:
            raw = "".join(
                part.get("text", "")
                for part in response["candidates"][0]["content"]["parts"]
                if isinstance(part, dict)
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Vertex stage {stage} response contains no candidate text") from exc
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Vertex stage {stage} returned non-JSON output") from exc
        usage_raw = response.get("usageMetadata", {})
        usage = {
            "input_tokens": int(usage_raw.get("promptTokenCount", 0) or 0),
            "output_tokens": int(usage_raw.get("candidatesTokenCount", 0) or 0),
            "reasoning_tokens": int(usage_raw.get("thoughtsTokenCount", 0) or 0),
            "total_tokens": int(usage_raw.get("totalTokenCount", 0) or 0),
        }
        return StageResult(
            stage=stage,
            paper_id=paper_id,
            payload=payload,
            provider="google_vertex",
            model=self.model_id,
            generation_mode="live",
            response_sha256=sha256_json(payload),
            usage=usage,
            duration_ms=duration_ms,
        )
