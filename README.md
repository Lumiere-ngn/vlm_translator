# VLM_translator

VLM_translator is a planned Python pipeline for retrieving Ontario traffic law text, parsing Part X of the Highway Traffic Act into JSON, and sending selected law records to a llama.cpp-backed LLM with a user-provided prompt.

Current status: documentation scaffold only. This repository has no Python implementation, config file, dependency file, or runnable commands yet.

## Planned Workflow

The implemented pipeline will:

1. Fetch the Ontario Highway Traffic Act from the Ontario e-Laws source.
2. Extract only Part X, "Rules of the Road".
3. Save parsed law records with `title`, `section_number`, and `content`.
4. Reuse the parsed-law cache on later runs when it already exists and validates.
5. Send all or selected law records to a llama.cpp LLM.
6. Save model outputs as JSON.

## Planned Setup

Use Python's built-in virtual environment support:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Conda is not required for the Python pipeline. It may still be useful separately if you want to manage GPU libraries or llama.cpp build dependencies.

## Planned llama.cpp Server

The pipeline will assume llama.cpp is already running as an OpenAI-compatible HTTP server:

```bash
./llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
```

Expected chat completions URL:

```text
http://localhost:8080/v1/chat/completions
```

## Planned Config File

A future `config.toml` will control the runtime behavior. It is expected to include:

```toml
source_url = "https://www.ontario.ca/laws/statute/90h08#BK230"
parsed_laws_path = "data/laws.json"
prompt_path = "prompts/default.txt"
results_path = "data/results.json"
law_sections = []

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
```

If `law_sections` is empty, every parsed Part X law will be processed. If it contains values such as `["133", "134"]`, only those sections will be sent to the LLM.

## Planned Commands

Once implemented, expected commands are:

```bash
python -m vlm_translator parse --config config.toml
python -m vlm_translator run --config config.toml
```

The parse command will create or reuse the parsed-law cache. The run command will reuse valid parsed laws unless forced to refresh.

## Repository Scope

This initial scaffold intentionally creates only:

- `AGENTS.md`
- `README.md`
- a local Git repository

No source code, config file, dependency file, tests, or generated data files are included yet.

