# VLM_translator

VLM_translator is a Python CLI pipeline for turning Ontario Highway Traffic Act text into structured, vision-oriented prompts for downstream VLM work.

The current workflow retrieves Part X of Ontario's Highway Traffic Act, parses the individual law sections into JSON records, and sends selected records to a llama.cpp-backed LLM. The default prompt asks the LLM to translate each statute into atomic visual questions that could be answered from dashcam-style video evidence.

This project does **not** run video inference itself. It prepares legal text for later VLM evaluation by converting statutes into structured, visually checkable question sets.

## What the pipeline does

1. Retrieves the Ontario Highway Traffic Act from the Ontario e-Laws API.
2. Extracts only Part X, **Rules of the Road**.
3. Parses each section into a record with:
   - `title`
   - `section_number`
   - `content`
4. Saves or reuses the parsed-law cache at `data/laws.json`.
5. Renders a prompt for each selected law section.
6. Calls a local llama.cpp OpenAI-compatible chat-completions server.
7. Parses the LLM response as JSON.
8. Optionally validates the response against a JSON Schema.
9. Writes pipeline outputs to `data/results.json`.

## Repository layout

```text
.
├── config.toml                    # Runtime configuration
├── data/
│   ├── laws.json                  # Parsed Part X law cache
│   └── results.json               # Generated LLM outputs
├── prompts/
│   └── default.txt                # Default legal-to-vision prompt
├── scripts/
│   ├── build_llama_cpp.sh          # Clone/build llama.cpp locally
│   └── run_llama_server.sh         # Start llama.cpp server
├── src/vlm_translator/
│   ├── cli.py                     # Typer CLI entrypoint
│   ├── config.py                  # TOML config loading
│   ├── llm.py                     # llama.cpp client and JSON validation
│   ├── models.py                  # Pydantic data models
│   ├── ontario_laws.py            # Retrieval, parsing, cache handling
│   ├── pipeline.py                # End-to-end orchestration
│   └── prompting.py               # Prompt rendering
├── tests/                         # pytest test suite
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Requirements

- Python 3.11+
- `git`
- `cmake`
- A local GGUF model for llama.cpp
- CUDA toolchain if you want GPU acceleration; otherwise llama.cpp can be built CPU-only

Python dependencies are listed in `requirements.txt` and `pyproject.toml`.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the package in editable mode:

```bash
pip install -e .
```

For development and tests:

```bash
pip install -e '.[test]'
```

You can also install from the requirements files:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Start the llama.cpp server

Start the local OpenAI-compatible server with a GGUF model:

```bash
bash scripts/run_llama_server.sh --model /path/to/model.gguf
```

By default, the server binds to:

```text
http://127.0.0.1:8080/v1/chat/completions
```

To choose a specific GPU:

```bash
bash scripts/run_llama_server.sh --model /path/to/model.gguf --gpu 0
```

To pass extra llama.cpp arguments, put them after `--`:

```bash
bash scripts/run_llama_server.sh --model /path/to/model.gguf --gpu 2 -- --ctx-size 8192
```

The run script defaults llama.cpp reasoning mode to `off` unless you override it. This matters because the pipeline expects JSON in the chat message `content` field.

## Configuration

The default configuration is in `config.toml`:

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
model = "models/Qwen3-14B-GGUF/Qwen3-14B-Q4_K_M.gguf"
temperature = 0.0
max_tokens = 2048

[pipeline]
force_refresh = false
fail_fast = false
retries = 2
timeout_seconds = 60.0
```

Important fields:

| Field | Meaning |
|---|---|
| `source_url` | Ontario e-Laws page used to resolve the API endpoint. |
| `parsed_laws_path` | JSON cache path for parsed law records. |
| `prompt_path` | Prompt template used for each law section. |
| `results_path` | Output path for LLM results. |
| `law_sections` | Section filter. Empty list means process all parsed sections. |
| `output_schema_path` | Optional JSON Schema file for validating each LLM response. |
| `llm.base_url` | llama.cpp OpenAI-compatible chat-completions endpoint. |
| `llm.model` | Model identifier sent in the chat-completions payload. |
| `pipeline.retries` | Number of retries after the first LLM attempt. |
| `pipeline.fail_fast` | If `true`, stop on first processing error. If `false`, record errors and continue. |

Relative paths in the config are resolved relative to the config file location.

## Prompt templates

Prompt templates may use any of these placeholders:

```text
{{law_json}}
{{title}}
{{section_number}}
{{content}}
```

If a prompt contains no placeholder, the pipeline appends the law JSON automatically.

The default prompt asks the model to return one JSON object containing a `law_id` and a list of atomic visual questions. Each question should be answerable as `True`, `False`, or `Uncertain`.

## Commands

Parse laws and create or reuse the cache:

```bash
python -m vlm_translator parse --config config.toml
```

Run the full pipeline:

```bash
python -m vlm_translator run --config config.toml
```

If installed with `pip install -e .`, the console script is also available:

```bash
vlm-translator parse --config config.toml
vlm-translator run --config config.toml
```

Useful overrides:

```bash
python -m vlm_translator parse --config config.toml --force-refresh
python -m vlm_translator run --config config.toml --law-section 133 --law-section 134
python -m vlm_translator run --config config.toml --prompt-path prompts/default.txt --results-path data/results.json
```

## Cache behavior

Before retrieving or parsing laws, the pipeline checks `parsed_laws_path`.

- If the cache exists and validates, it is reused.
- If the cache is missing or invalid, the source is retrieved and parsed again.
- `--force-refresh` or `force_refresh = true` ignores the cache.
- Changes to the prompt, selected law sections, model, or result path do not invalidate the parsed-law cache.

The committed `data/laws.json` cache currently contains parsed Part X records from the Ontario Highway Traffic Act. Regenerate it when the source changes or when parser behavior changes.

## Output format

Each processed law produces a result object similar to:

```json
{
  "section_number": "136",
  "title": "Stop at through highway",
  "llm_output": {
    "law_id": "HTA_136",
    "questions": [
      {
        "id": "C1",
        "type": "CONDITION",
        "text": "Is there a stop sign visible facing the ego vehicle?",
        "allowed_responses": ["True", "False", "Uncertain"]
      }
    ]
  },
  "raw_response": "{...}",
  "status": "ok",
  "error": null
}
```

If a section fails and `fail_fast = false`, the result is written with `status = "error"` and the error message is stored in `error`.

## Notes and limitations

- The parser is tailored to the structure of Ontario e-Laws HTML for the Highway Traffic Act.
- The project preserves source law text for transformation, but it does not provide legal advice.
- The quality of generated VLM questions depends heavily on the prompt and the local model.
- JSON validation only guarantees structural conformity to a schema; it does not guarantee legal correctness or visual usefulness.
- Local GGUF models are not downloaded by this repository.
