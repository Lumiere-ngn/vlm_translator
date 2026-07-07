from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from config import load_config
from pipeline import parse_laws, run_pipeline

app = typer.Typer(help="Parse Ontario traffic laws and process them with a llama.cpp LLM.")


def _load_config_with_overrides(
    config_path: Path,
    *,
    force_refresh: bool | None = None,
    law_section: list[str] | None = None,
    prompt_path: Path | None = None,
    results_path: Path | None = None,
):
    config = load_config(config_path)
    updates = config.model_dump()
    if force_refresh is not None:
        pipeline = config.pipeline.model_dump()
        pipeline["force_refresh"] = force_refresh
        updates["pipeline"] = pipeline
    if law_section:
        updates["law_sections"] = law_section
    if prompt_path is not None:
        updates["prompt_path"] = prompt_path
    if results_path is not None:
        updates["results_path"] = results_path
    return type(config).model_validate(updates)


@app.command()
def parse(
    config: Annotated[Path, typer.Option("--config", "-c", help="Path to config.toml.")] = Path("config.toml"),
    force_refresh: Annotated[bool, typer.Option("--force-refresh", help="Ignore parsed-law cache.")] = False,
) -> None:
    """Fetch and parse Part X laws, or reuse a valid parsed-law cache."""
    parsed_config = _load_config_with_overrides(config, force_refresh=force_refresh)
    cache = parse_laws(parsed_config)
    typer.echo(f"Parsed law cache ready: {parsed_config.parsed_laws_path}")
    typer.echo(f"Law records: {len(cache.laws)}")


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", help="Path to config.toml.")] = Path("config.toml"),
    force_refresh: Annotated[bool, typer.Option("--force-refresh", help="Ignore parsed-law cache.")] = False,
    law_section: Annotated[
        list[str] | None,
        typer.Option("--law-section", help="Section number to process. Repeat for multiple sections."),
    ] = None,
    prompt_path: Annotated[Path | None, typer.Option("--prompt-path", help="Override prompt path.")] = None,
    results_path: Annotated[Path | None, typer.Option("--results-path", help="Override result path.")] = None,
) -> None:
    """Run parsing/cache lookup and send selected laws to llama.cpp."""
    parsed_config = _load_config_with_overrides(
        config,
        force_refresh=force_refresh,
        law_section=law_section,
        prompt_path=prompt_path,
        results_path=results_path,
    )
    results = run_pipeline(parsed_config)
    ok_count = sum(1 for result in results if result.status == "ok")
    error_count = len(results) - ok_count
    typer.echo(f"Results written: {parsed_config.results_path}")
    typer.echo(f"Processed: {len(results)} ok={ok_count} errors={error_count}")
