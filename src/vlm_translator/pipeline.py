from __future__ import annotations

import json
from pathlib import Path

from .llm import call_llama_cpp, load_json_schema
from .models import AppConfig, PipelineResult
from .ontario_laws import filter_laws, get_or_parse_laws
from .prompting import render_prompt


def parse_laws(config: AppConfig):
    return get_or_parse_laws(
        config.source_url,
        config.parsed_laws_path,
        force_refresh=config.pipeline.force_refresh,
        timeout_seconds=config.pipeline.timeout_seconds,
    )


def run_pipeline(config: AppConfig) -> list[PipelineResult]:
    cache = parse_laws(config)
    laws = filter_laws(cache.laws, config.law_sections)
    prompt_template = config.prompt_path.read_text(encoding="utf-8")
    output_schema = load_json_schema(config.output_schema_path)

    results: list[PipelineResult] = []
    for law in laws:
        try:
            prompt = render_prompt(prompt_template, law)
            llm_output, raw_response = call_llama_cpp(
                prompt,
                config.llm,
                retries=config.pipeline.retries,
                timeout_seconds=config.pipeline.timeout_seconds,
                output_schema=output_schema,
            )
            results.append(
                PipelineResult(
                    section_number=law.section_number,
                    title=law.title,
                    llm_output=llm_output,
                    raw_response=raw_response,
                    status="ok",
                )
            )
        except Exception as exc:
            if config.pipeline.fail_fast:
                raise
            results.append(
                PipelineResult(
                    section_number=law.section_number,
                    title=law.title,
                    status="error",
                    error=str(exc),
                )
            )

    write_results(config.results_path, results)
    return results


def write_results(path: str | Path, results: list[PipelineResult]) -> None:
    results_path = Path(path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [result.model_dump() for result in results]
    results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

