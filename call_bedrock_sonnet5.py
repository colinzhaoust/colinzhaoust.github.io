#!/usr/bin/env python3
"""Minimal Python smoke test for Claude Sonnet 5 on Amazon Bedrock.

This example reads a local Bedrock API key from temp_env.txt and calls the
Bedrock Converse API through the AWS CLI. It uses the CLI because this local
workspace does not currently have boto3 installed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / "temp_env.txt"
DEFAULT_REGION = "us-east-1"
DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-5"
DEFAULT_PROMPT = "Say hello in one short friendly sentence."


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def call_bedrock(prompt: str) -> str:
    config = load_env_file(ENV_FILE)
    token = config.get("AWS_BEARER_TOKEN_BEDROCK")
    if not token:
        raise RuntimeError(f"Missing AWS_BEARER_TOKEN_BEDROCK in {ENV_FILE}")

    region = config.get("AWS_REGION", DEFAULT_REGION)
    model_id = config.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
    messages = [{"role": "user", "content": [{"text": prompt}]}]

    env = os.environ.copy()
    env["AWS_BEARER_TOKEN_BEDROCK"] = token
    env["AWS_EC2_METADATA_DISABLED"] = "true"

    # Force this sample to use the Bedrock API key instead of any local IAM profile.
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
        env.pop(name, None)

    result = subprocess.run(
        [
            "aws",
            "bedrock-runtime",
            "converse",
            "--region",
            region,
            "--model-id",
            model_id,
            "--messages",
            json.dumps(messages),
            "--inference-config",
            json.dumps({"maxTokens": 128}),
            "--query",
            "output.message.content[0].text",
            "--output",
            "text",
        ],
        check=True,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or DEFAULT_PROMPT
    print(call_bedrock(prompt))


if __name__ == "__main__":
    main()
