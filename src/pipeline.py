from __future__ import annotations

import json
from pathlib import Path

from llm import call_llama_cpp, load_json_schema
from models import (
    AppConfig,
    MonitorStatute,
    PipelineIssue,
    PipelineRunResult,
    StatuteCatalog,
    TranslatedLawOutput,
)
from ontario_laws import filter_laws, get_or_parse_laws
from prompting import render_prompt


def parse_laws(config: AppConfig):
    return get_or_parse_laws(
        config.source_url,
        config.parsed_laws_path,
        force_refresh=config.pipeline.force_refresh,
        timeout_seconds=config.pipeline.timeout_seconds,
    )


def run_pipeline(config: AppConfig) -> PipelineRunResult:
    cache = parse_laws(config)
    laws = filter_laws(cache.laws, config.law_sections)
    prompt_template = config.prompt_path.read_text(encoding="utf-8")
    output_schema = load_json_schema(config.output_schema_path)

    statutes: list[MonitorStatute] = []
    issues: list[PipelineIssue] = []
    seen_ids: set[str] = set()
    for law in laws:
        try:
            prompt = render_prompt(prompt_template, law)
            llm_output, _raw_response = call_llama_cpp(
                prompt,
                config.llm,
                retries=config.pipeline.retries,
                timeout_seconds=config.pipeline.timeout_seconds,
                output_schema=output_schema,
            )
            translated = TranslatedLawOutput.model_validate(llm_output)
            if translated.law_id in seen_ids:
                raise ValueError(f"duplicate law_id {translated.law_id!r}")
            seen_ids.add(translated.law_id)
            statutes.append(
                MonitorStatute(
                    id=translated.law_id,
                    article=law.section_number,
                    name=law.title,
                    statute_text=law.content,
                    sub_questions=translated.questions,
                )
            )
        except Exception as exc:
            if config.pipeline.fail_fast:
                raise
            issues.append(
                PipelineIssue(
                    section_number=law.section_number,
                    title=law.title,
                    error=str(exc),
                )
            )

    if not statutes:
        raise RuntimeError("No statutes were translated successfully; refusing to write an empty catalog.")

    catalog = StatuteCatalog(statutes=statutes)
    write_results(config.results_path, catalog)
    return PipelineRunResult(catalog=catalog, issues=issues)


def write_results(path: str | Path, catalog: StatuteCatalog) -> None:
    results_path = Path(path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    payload = catalog.model_dump(mode="json")
    results_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
