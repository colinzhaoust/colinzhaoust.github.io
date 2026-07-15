#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="$script_dir/temp_env.txt"

if [[ ! -f "$env_file" ]]; then
  echo "Missing env file: $env_file" >&2
  exit 2
fi

set -a
source "$env_file"
set +a

: "${AWS_BEARER_TOKEN_BEDROCK:?Missing AWS_BEARER_TOKEN_BEDROCK in temp_env.txt}"

# Keep this smoke test on the Bedrock API-key path, not any local IAM profile.
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE
export AWS_EC2_METADATA_DISABLED=true

prompt="${*:-Say hello in one short friendly sentence.}"
region="${AWS_REGION:-us-east-1}"
model_id="${BEDROCK_MODEL_ID:-us.anthropic.claude-sonnet-5}"

messages_json="$(
  python3 -c 'import json, sys; print(json.dumps([{"role": "user", "content": [{"text": " ".join(sys.argv[1:])}]}]))' "$prompt"
)"

aws bedrock-runtime converse \
  --region "$region" \
  --model-id "$model_id" \
  --messages "$messages_json" \
  --inference-config '{"maxTokens":128}' \
  --query 'output.message.content[0].text' \
  --output text
