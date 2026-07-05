# VLM_translator Agent Notes

## Project Purpose

VLM_translator is planned as a Python pipeline for processing Ontario traffic law text. The target workflow is:

1. Retrieve the Ontario Highway Traffic Act from the Ontario e-Laws website.
2. Parse only Part X, "Rules of the Road", into structured JSON records.
3. Send each selected law record to a llama.cpp-backed LLM with a user-provided prompt.
4. Store each LLM response as JSON in a configured output path.

The current repository state is a documentation scaffold only. Do not assume Python source, dependency files, or runtime config exist until they are added in a later implementation step.

## Environment

Use Python's built-in virtual environment tooling. Conda is not required for this project because the Python pipeline only needs ordinary Python packages and calls llama.cpp over HTTP.

Expected setup once dependencies are added:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Keep `.venv/` out of version control.

## Planned Pipeline Architecture

The future implementation should be config-driven and split into focused modules:

- Retrieval: resolve the configured source URL to the Ontario e-Laws API endpoint and fetch statute content.
- Parsing: extract Part X only, stop before Part X.1, and produce law records with `title`, `section_number`, and `content`.
- Cache: write parsed law records to a configured JSON path and reuse them on later runs.
- Prompt rendering: combine each selected law record with the configured prompt template.
- LLM client: call a llama.cpp OpenAI-compatible HTTP endpoint.
- Results: write one result object per processed law to the configured output path.

## Planned Config Behavior

Use a config file for runtime choices, including:

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

## LLM Expectations

Assume llama.cpp is running as an OpenAI-compatible HTTP server, for example:

```bash
./llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
```

The pipeline should call a chat completions endpoint such as:

```text
http://localhost:8080/v1/chat/completions
```

The prompt is expected to instruct the model to return JSON. The implementation should parse and validate the response as JSON, retry when configured, and record errors without losing other completed results.

## Coding Expectations

- Keep implementation small and modular.
- Prefer typed data models for config, parsed laws, and LLM results.
- Preserve original law text content as faithfully as practical while removing table-of-contents and amendment-note noise.
- Do not provide legal advice; this project extracts and transforms text.
- Add tests for parsing, cache behavior, config handling, and LLM response validation.

