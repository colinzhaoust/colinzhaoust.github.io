#!/usr/bin/env bash
# Submit on Babel with: sbatch docs/ops/babel-qwen3-8b-vllm.sbatch
# After ready-<job>.json appears, tunnel from the client with:
# ssh -N -L 18081:127.0.0.1:18080 -J babel xinranz3@<compute-host>
# The OpenAI-compatible base URL is then http://127.0.0.1:18081/v1.
#SBATCH --job-name=qwen3-8b-vllm
#SBATCH --partition=general
#SBATCH --account=sherryw
#SBATCH --gres=gpu:L40S:1
#SBATCH --exclude=babel-s5-24
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=/home/xinranz3/4blue2brown_explore/runs/qwen3_vllm/slurm-%j.out
#SBATCH --error=/home/xinranz3/4blue2brown_explore/runs/qwen3_vllm/slurm-%j.err

set -euo pipefail

MODEL_ID="${MODEL_ID:-Qwen/Qwen3-8B}"
MODEL_REVISION="${MODEL_REVISION:-895c8d171bc03c30e113cd7a28c02494b5e068b7}"
PORT="${PORT:-18080}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
VLLM_VERSION="${VLLM_VERSION:-0.9.2}"
TRANSFORMERS_VERSION="${TRANSFORMERS_VERSION:-4.53.2}"

BASE_PY=/home/xinranz3/miniconda3/envs/vllm/bin/python
ENV_ROOT="/home/xinranz3/vllm-qwen3-${VLLM_VERSION}"
STATE_DIR=/home/xinranz3/4blue2brown_explore/runs/qwen3_vllm
SCRATCH_ROOT="/tmp/${USER}/qwen3-vllm-${SLURM_JOB_ID}"
SERVER_LOG="${STATE_DIR}/server-${SLURM_JOB_ID}.log"
READY_FILE="${STATE_DIR}/ready-${SLURM_JOB_ID}.json"

mkdir -p "$STATE_DIR" "$SCRATCH_ROOT"
chmod 700 "$STATE_DIR"
cd "$SCRATCH_ROOT"

export UV_CACHE_DIR="${SCRATCH_ROOT}/uv-cache"
export HF_HOME="${SCRATCH_ROOT}/huggingface"
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn

echo "job_id=${SLURM_JOB_ID}"
echo "host=$(hostname)"
echo "model=${MODEL_ID}"
echo "revision=${MODEL_REVISION}"
echo "port=${PORT}"
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader

if [ ! -x "${ENV_ROOT}/bin/vllm" ]; then
  echo "Creating isolated ${ENV_ROOT}"
  "$BASE_PY" -m venv "$ENV_ROOT"
  "${ENV_ROOT}/bin/python" -m pip install --upgrade pip uv
fi

"${ENV_ROOT}/bin/uv" pip install \
  --python "${ENV_ROOT}/bin/python" \
  --torch-backend=auto \
  "vllm==${VLLM_VERSION}" \
  "transformers==${TRANSFORMERS_VERSION}"

"${ENV_ROOT}/bin/python" -c \
  'from importlib.metadata import version; print("runtime", version("vllm"), version("transformers"), version("torch"))'

"${ENV_ROOT}/bin/vllm" serve "$MODEL_ID" \
  --revision "$MODEL_REVISION" \
  --served-model-name "$MODEL_ID" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.90 \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-seqs 8 \
  --enable-reasoning \
  --reasoning-parser qwen3 \
  --disable-log-requests \
  > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Waiting for the OpenAI-compatible endpoint"
READY=0
for _ in $(seq 1 360); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "vLLM exited before readiness"
    tail -80 "$SERVER_LOG"
    exit 31
  fi
  STATUS=$(curl -s -m 5 -o /dev/null -w '%{http_code}' \
    "http://127.0.0.1:${PORT}/health" || true)
  if [ "$STATUS" = "200" ]; then
    READY=1
    break
  fi
  sleep 10
done

if [ "$READY" != "1" ]; then
  echo "vLLM did not become ready"
  tail -80 "$SERVER_LOG"
  exit 32
fi

HOSTNAME=$(hostname)
cat > "$READY_FILE" <<EOF
{
  "status": "ready",
  "job_id": "${SLURM_JOB_ID}",
  "host": "${HOSTNAME}",
  "port": ${PORT},
  "model": "${MODEL_ID}",
  "revision": "${MODEL_REVISION}",
  "vllm_version": "${VLLM_VERSION}",
  "max_model_len": ${MAX_MODEL_LEN},
  "access": "SSH jump tunnel to compute-node loopback"
}
EOF
chmod 600 "$READY_FILE"

SMOKE_RESPONSE="${SCRATCH_ROOT}/smoke-response.json"
curl -sS --fail \
  -H 'Content-Type: application/json' \
  "http://127.0.0.1:${PORT}/v1/chat/completions" \
  --data "{\"model\":\"${MODEL_ID}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly BABEL_QWEN3_OK\"}],\"temperature\":0,\"max_tokens\":32,\"chat_template_kwargs\":{\"enable_thinking\":false}}" \
  > "$SMOKE_RESPONSE"

"${ENV_ROOT}/bin/python" - "$SMOKE_RESPONSE" <<'PY'
import json
import sys

response = json.load(open(sys.argv[1], encoding="utf-8"))
content = response["choices"][0]["message"]["content"].strip()
if "BABEL_QWEN3_OK" not in content:
    raise SystemExit(f"unexpected smoke response: {content!r}")
print(json.dumps({"smoke_test": "PASS", "content": content, "usage": response.get("usage")}, sort_keys=True))
PY

echo "ready_file=${READY_FILE}"
echo "server_log=${SERVER_LOG}"
wait "$SERVER_PID"
