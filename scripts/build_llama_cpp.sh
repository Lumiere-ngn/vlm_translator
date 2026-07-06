#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/ggml-org/llama.cpp"
SOURCE_DIR="llama_cpp"
BUILD_DIR="${SOURCE_DIR}/build"
BUILD_TYPE="Release"
CUDA_ARCH="89"
UPDATE=0
FORCE_CPU=0
JOBS=""

usage() {
  cat <<'USAGE'
Usage: bash scripts/build_llama_cpp.sh [OPTIONS]

Clone and build llama.cpp for this project.

Options:
  --update            Fetch and update an existing llama_cpp checkout before building.
  --cpu-only          Force a CPU-only build even when CUDA is available.
  --jobs N, -j N      Parallel build jobs. Defaults to the build tool default.
  --help, -h          Show this help.

Defaults:
  source dir          llama_cpp/
  build dir           llama_cpp/build/
  CUDA compiler       /usr/local/cuda-12.3/bin/nvcc if present, else nvcc
  CUDA architecture   89 (NVIDIA L40S / Ada)
USAGE
}

log() {
  printf '[build_llama_cpp] %s\n' "$*"
}

fail() {
  printf '[build_llama_cpp] ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --update)
      UPDATE=1
      shift
      ;;
    --cpu-only)
      FORCE_CPU=1
      shift
      ;;
    --jobs|-j)
      [[ $# -ge 2 ]] || fail "--jobs requires a value"
      JOBS="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

command -v git >/dev/null 2>&1 || fail "git is required"
command -v cmake >/dev/null 2>&1 || fail "cmake is required"

if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  if [[ -e "${SOURCE_DIR}" ]]; then
    fail "${SOURCE_DIR} exists but is not a git checkout"
  fi
  log "Cloning llama.cpp into ${SOURCE_DIR}"
  git clone "${REPO_URL}" "${SOURCE_DIR}"
elif [[ "${UPDATE}" -eq 1 ]]; then
  log "Updating existing ${SOURCE_DIR} checkout"
  git -C "${SOURCE_DIR}" fetch --tags origin
  git -C "${SOURCE_DIR}" pull --ff-only
else
  log "Using existing ${SOURCE_DIR} checkout without updating"
fi

CUDA_COMPILER=""
if [[ "${FORCE_CPU}" -eq 0 ]]; then
  if [[ -x /usr/local/cuda-12.3/bin/nvcc ]]; then
    CUDA_COMPILER="/usr/local/cuda-12.3/bin/nvcc"
  elif command -v nvcc >/dev/null 2>&1; then
    CUDA_COMPILER="$(command -v nvcc)"
  fi
fi

CMAKE_ARGS=(
  -S "${SOURCE_DIR}"
  -B "${BUILD_DIR}"
  -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
)

BUILD_BACKEND="cpu"
if [[ -n "${CUDA_COMPILER}" ]]; then
  BUILD_BACKEND="cuda"
  log "CUDA compiler: ${CUDA_COMPILER}"
  "${CUDA_COMPILER}" --version || fail "Failed to run ${CUDA_COMPILER}"
  CMAKE_ARGS+=(
    -DGGML_CUDA=ON
    -DGGML_NATIVE=OFF
    -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH}"
    -DCMAKE_CUDA_COMPILER="${CUDA_COMPILER}"
  )
else
  log "CUDA compiler not found or CPU-only requested; building CPU-only llama.cpp"
fi

log "Configuring llama.cpp (${BUILD_BACKEND}, ${BUILD_TYPE})"
cmake "${CMAKE_ARGS[@]}"

BUILD_ARGS=(--build "${BUILD_DIR}" --config "${BUILD_TYPE}")
if [[ -n "${JOBS}" ]]; then
  BUILD_ARGS+=(-j "${JOBS}")
fi

log "Building llama.cpp"
cmake "${BUILD_ARGS[@]}"

BINARY_PATH="${BUILD_DIR}/bin/llama-server"
if [[ ! -x "${BINARY_PATH}" ]]; then
  fail "Expected llama-server binary was not found at ${BINARY_PATH}"
fi

COMMIT="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
CUDA_VERSION=""
if [[ -n "${CUDA_COMPILER}" ]]; then
  CUDA_VERSION="$("${CUDA_COMPILER}" --version | tr '\n' ' ' | sed 's/"/\\"/g')"
fi

cat > llama_cpp.build.json <<JSON
{
  "source_dir": "${SOURCE_DIR}",
  "build_dir": "${BUILD_DIR}",
  "binary_path": "${BINARY_PATH}",
  "repo_url": "${REPO_URL}",
  "commit": "${COMMIT}",
  "build_type": "${BUILD_TYPE}",
  "backend": "${BUILD_BACKEND}",
  "cuda_compiler": "${CUDA_COMPILER}",
  "cuda_version": "${CUDA_VERSION}",
  "cuda_architecture": "${CUDA_ARCH}",
  "created_at": "${TIMESTAMP}"
}
JSON

log "Build complete: ${BINARY_PATH}"
log "Manifest written: llama_cpp.build.json"

