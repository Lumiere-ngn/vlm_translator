# VLM_translator Agent Notes

## Project Purpose

VLM_translator is a Python pipeline for processing Ontario traffic law text. The target workflow is:

1. Retrieve the Ontario Highway Traffic Act from the Ontario e-Laws website.
2. Parse only Part X, "Rules of the Road", into structured JSON records.
3. Send each selected law record to a llama.cpp-backed LLM with a user-provided prompt.
4. Store each LLM response as JSON in a configured output path.

The project is config-driven and uses a parsed-law cache to avoid unnecessary retrieval and parsing.

## Environment

Use Python's built-in virtual environment tooling. Conda is not required for this project because the Python pipeline only needs ordinary Python packages and calls llama.cpp over HTTP.

Expected setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Keep `.venv/` out of version control.

## Pipeline Architecture

The implementation is config-driven and split into focused modules:

- `src/vlm_translator/ontario_laws.py`: resolves the configured source URL to the Ontario e-Laws API endpoint, fetches statute content, parses Part X only, writes the parsed-law cache, and reuses it when valid.
- `src/vlm_translator/prompting.py`: combines each selected law record with the configured prompt template.
- `src/vlm_translator/llm.py`: calls a llama.cpp OpenAI-compatible HTTP endpoint and validates JSON responses.
- `src/vlm_translator/pipeline.py`: coordinates cache lookup, prompt rendering, LLM calls, and result writing.
- `src/vlm_translator/cli.py`: exposes `parse` and `run` commands.

## Config Behavior

Use `config.toml` for runtime choices, including:

- which LLM endpoint and model to use
- which source law URL to retrieve
- which law sections to process
- where to read the prompt from
- where to write parsed laws and final results
- whether to force a fresh retrieval and parse

If the configured law section list is empty, process every parsed law from Part X. If it contains section numbers, process only exact matches.

## Cache Rule

Before retrieving or parsing laws, check whether the configured parsed-laws JSON file already exists and validates against the expected schema.

- If it exists, validates, and force refresh is disabled, use the cached parsed laws.
- If it is missing, invalid, or force refresh is enabled, retrieve and parse the source again.

Changing the prompt, selected law sections, model, or output path should not invalidate the parsed-law cache.

## Commands

```bash
python -m vlm_translator parse --config config.toml
python -m vlm_translator run --config config.toml
```

Use `--force-refresh` to ignore the parsed-law cache.

## LLM Expectations

Assume llama.cpp is running as an OpenAI-compatible HTTP server. The repository provides scripts for building and running it locally:

```bash
bash scripts/build_llama_cpp.sh
bash scripts/run_llama_server.sh --model /path/to/model.gguf
```

The pipeline should call a chat completions endpoint such as:

```text
http://localhost:8080/v1/chat/completions
```

The prompt is expected to instruct the model to return JSON. The implementation should parse and validate the response as JSON, retry when configured, and record errors without losing other completed results.

The build script clones llama.cpp into `llama_cpp/`, which is intentionally ignored by Git. It prefers `/usr/local/cuda-12.3/bin/nvcc`, falls back to `nvcc`, builds CUDA architecture `89` when CUDA is available, and otherwise builds CPU-only. The run script leaves `CUDA_VISIBLE_DEVICES` unchanged by default; pass `--gpu 0`, `--gpu 1`, or another CUDA-visible device list to restrict runtime GPU selection.

Do not commit llama.cpp source, build output, `llama_cpp.build.json`, or model files.

## Coding Expectations

- Keep implementation small and modular.
- Prefer typed data models for config, parsed laws, and LLM results.
- Preserve original law text content as faithfully as practical while removing table-of-contents and amendment-note noise.
- Do not provide legal advice; this project extracts and transforms text.
- Add tests for parsing, cache behavior, config handling, and LLM response validation.
