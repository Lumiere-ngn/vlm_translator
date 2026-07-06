from pathlib import Path

from vlm_translator.config import load_config
from vlm_translator.models import LawRecord
from vlm_translator.prompting import render_prompt


def test_load_config_resolves_relative_paths(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
source_url = "https://www.ontario.ca/laws/statute/90h08#BK230"
parsed_laws_path = "data/laws.json"
prompt_path = "prompts/default.txt"
results_path = "data/results.json"
law_sections = ["133"]
output_schema_path = ""

[llm]
provider = "llama_cpp"
base_url = "http://localhost:8080/v1/chat/completions"
model = "local-model"

[pipeline]
force_refresh = false
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.parsed_laws_path == tmp_path / "data/laws.json"
    assert config.prompt_path == tmp_path / "prompts/default.txt"
    assert config.results_path == tmp_path / "data/results.json"
    assert config.law_sections == ["133"]
    assert config.output_schema_path is None


def test_render_prompt_replaces_placeholders():
    law = LawRecord(title="Title", section_number="133", content="Content")

    rendered = render_prompt("Translate {{section_number}}: {{title}}\n{{content}}", law)

    assert "Translate 133: Title" in rendered
    assert "Content" in rendered


def test_render_prompt_appends_json_when_no_placeholders():
    law = LawRecord(title="Title", section_number="133", content="Content")

    rendered = render_prompt("Summarize this.", law)

    assert "Law JSON:" in rendered
    assert '"section_number": "133"' in rendered

