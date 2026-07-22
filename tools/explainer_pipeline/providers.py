from __future__ import annotations

import json
import os
import subprocess
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
            "--query",
            "output.message.content[0].text",
            "--output",
            "text",
        ]
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
        raw = completed.stdout.strip()
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
        )
