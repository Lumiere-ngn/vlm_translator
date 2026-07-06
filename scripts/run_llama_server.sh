#!/usr/bin/env bash
set -euo pipefail

BINARY_PATH="llama_cpp/build/bin/llama-server"
MODEL_PATH=""
HOST="127.0.0.1"
PORT="8080"
CUDA_DEVICES="${CUDA_VISIBLE_DEVICES:-}"
EXTRA_ARGS=()
REASONING_ARG_SEEN=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/run_llama_server.sh --model /path/to/model.gguf [OPTIONS] [-- EXTRA_ARGS...]

Start the project llama.cpp server.

Options:
  --model PATH        Required GGUF model path.
  --host HOST         Bind host. Default: 127.0.0.1
  --port PORT         Bind port. Default: 8080
  --binary PATH       llama-server path. Default: llama_cpp/build/bin/llama-server
  --gpu DEVICES      CUDA_VISIBLE_DEVICES value. Default: leave unchanged
  --reasoning MODE   Pass through llama.cpp reasoning mode. Default: off
  --help, -h          Show this help.

Examples:
  bash scripts/run_llama_server.sh --model /models/model.gguf
  bash scripts/run_llama_server.sh --model /models/model.gguf --gpu 2 -- --ctx-size 8192
USAGE
}

fail() {
  printf '[run_llama_server] ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      [[ $# -ge 2 ]] || fail "--model requires a path"
      MODEL_PATH="$2"
      shift 2
      ;;
    --host)
      [[ $# -ge 2 ]] || fail "--host requires a value"
      HOST="$2"
      shift 2
      ;;
    --port)
      [[ $# -ge 2 ]] || fail "--port requires a value"
      PORT="$2"
      shift 2
      ;;
    --binary)
      [[ $# -ge 2 ]] || fail "--binary requires a path"
      BINARY_PATH="$2"
      shift 2
      ;;
    --gpu)
      [[ $# -ge 2 ]] || fail "--gpu requires a CUDA_VISIBLE_DEVICES value"
      CUDA_DEVICES="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
      ;;
    --reasoning|-rea)
      [[ $# -ge 2 ]] || fail "$1 requires a value"
      REASONING_ARG_SEEN=1
      EXTRA_ARGS+=("$1" "$2")
      shift 2
      ;;
    --reasoning=*)
      REASONING_ARG_SEEN=1
      EXTRA_ARGS+=("$1")
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

for arg in "${EXTRA_ARGS[@]}"; do
  case "${arg}" in
    --reasoning|-rea|--reasoning=*)
      REASONING_ARG_SEEN=1
      ;;
  esac
done

if [[ "${REASONING_ARG_SEEN}" -eq 0 ]]; then
  EXTRA_ARGS+=("--reasoning" "off")
fi

[[ -n "${MODEL_PATH}" ]] || fail "--model /path/to/model.gguf is required"
[[ -f "${MODEL_PATH}" ]] || fail "Model file does not exist: ${MODEL_PATH}"
[[ -x "${BINARY_PATH}" ]] || fail "llama-server not found or not executable: ${BINARY_PATH}. Run scripts/build_llama_cpp.sh first."

if [[ -n "${CUDA_DEVICES}" ]]; then
  printf '[run_llama_server] CUDA_VISIBLE_DEVICES=%s\n' "${CUDA_DEVICES}"
  export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"
else
  printf '[run_llama_server] CUDA_VISIBLE_DEVICES is unset; all CUDA-visible GPUs may be used by llama.cpp\n'
fi
printf '[run_llama_server] Starting %s on %s:%s\n' "${BINARY_PATH}" "${HOST}" "${PORT}"

exec "${BINARY_PATH}" \
  --model "${MODEL_PATH}" \
  --host "${HOST}" \
  --port "${PORT}" \
  "${EXTRA_ARGS[@]}"
