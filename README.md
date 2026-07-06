# VLM_translator

VLM_translator is a Python pipeline for retrieving Ontario traffic law text, parsing Part X of the Highway Traffic Act into JSON, and sending selected law records to a llama.cpp-backed LLM with a user-provided prompt.

Current status: initial CLI implementation with parser, parsed-law cache, config loading, prompt rendering, llama.cpp HTTP client, and tests.

## Workflow

The pipeline:

1. Fetch the Ontario Highway Traffic Act from the Ontario e-Laws source.
2. Extract only Part X, "Rules of the Road".
3. Save parsed law records with `title`, `section_number`, and `content`.
4. Reuse the parsed-law cache on later runs when it already exists and validates.
5. Send all or selected law records to a llama.cpp LLM.
6. Save model outputs as JSON.

## Setup

Use Python's built-in virtual environment support:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Conda is not required for the Python pipeline. It may still be useful separately if you want to manage GPU libraries or llama.cpp build dependencies.

## llama.cpp Server

The pipeline assumes llama.cpp is running as an OpenAI-compatible HTTP server. Build it locally with:

```bash
bash scripts/build_llama_cpp.sh
```

This clones `https://github.com/ggml-org/llama.cpp` into `llama_cpp/` and builds `llama-server`. The script prefers `/usr/local/cuda-12.3/bin/nvcc` when present, then falls back to `nvcc`. With CUDA available, it builds for CUDA architecture `89`, which matches NVIDIA L40S/Ada hardware. Without CUDA, it builds CPU-only and prints a warning.

Start the server with a local GGUF model:

```bash
bash scripts/run_llama_server.sh --model /path/to/model.gguf
```

Expected chat completions URL:

```text
http://localhost:8080/v1/chat/completions
```

By default, the run script leaves `CUDA_VISIBLE_DEVICES` unchanged so llama.cpp can use the GPUs visible in the current shell. To restrict the server to a specific GPU, pass `--gpu`:

```bash
bash scripts/run_llama_server.sh --model /path/to/model.gguf --gpu 0
```

Model files are not downloaded by this project. Provide a local `.gguf` model path.

## Config File

`config.toml` controls the runtime behavior:

```toml
source_url = "https://www.ontario.ca/laws/statute/90h08#BK230"
parsed_laws_path = "data/laws.json"
prompt_path = "prompts/default.txt"
results_path = "data/results.json"
law_sections = []
output_schema_path = ""

[llm]
provider = "llama_cpp"
base_url = "http://localhost:8080/v1/chat/completions"
model = "local-model"
temperature = 0.0
max_tokens = 2048

[pipeline]
force_refresh = false
fail_fast = false
retries = 2
timeout_seconds = 60.0
```

If `law_sections` is empty, every parsed Part X law will be processed. If it contains values such as `["133", "134"]`, only those sections will be sent to the LLM.

`output_schema_path` is optional. If set, it should point to a JSON Schema file used to validate each LLM JSON response.

## Commands

```bash
python -m vlm_translator parse --config config.toml
python -m vlm_translator run --config config.toml
```

The parse command creates or reuses the parsed-law cache. The run command reuses valid parsed laws unless forced to refresh.

Useful overrides:

```bash
python -m vlm_translator parse --config config.toml --force-refresh
python -m vlm_translator run --config config.toml --law-section 133 --law-section 134
python -m vlm_translator run --config config.toml --prompt-path prompts/default.txt --results-path data/results.json
```

## Cache Behavior

Before retrieving or parsing laws, the pipeline checks `parsed_laws_path`.

- If the cache exists and validates, it is reused.
- If the cache is missing or invalid, the source is retrieved and parsed again.
- `--force-refresh` or `force_refresh = true` ignores the cache.
- Prompt, model, selected sections, and output path changes do not invalidate the parsed-law cache.

## Tests

Install dev dependencies and run:

```bash
pip install -r requirements-dev.txt
pytest
```

## Local llama.cpp Files

The `llama_cpp/` source/build directory and `llama_cpp.build.json` manifest are ignored by Git. They are local machine artifacts, not project source. Another user can recreate them by running:

```bash
bash scripts/build_llama_cpp.sh
```
