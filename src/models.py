from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMConfig(BaseModel):
    provider: str = "llama_cpp"
    base_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    model: str = "local-model"
    temperature: float = 0.0
    max_tokens: int = 2048


class PipelineOptions(BaseModel):
    force_refresh: bool = False
    fail_fast: bool = False
    retries: int = 2
    timeout_seconds: float = 60.0


class AppConfig(BaseModel):
    source_url: str = "https://www.ontario.ca/laws/statute/90h08#BK230"
    parsed_laws_path: Path = Path("data/laws.json")
    prompt_path: Path = Path("prompts/default.txt")
    results_path: Path = Path("data/results.json")
    law_sections: list[str] = Field(default_factory=list)
    output_schema_path: Path | None = None
    llm: LLMConfig = Field(default_factory=LLMConfig)
    pipeline: PipelineOptions = Field(default_factory=PipelineOptions)

    @field_validator("law_sections", mode="before")
    @classmethod
    def normalize_law_sections(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("output_schema_path", mode="before")
    @classmethod
    def normalize_schema_path(cls, value: Any) -> Path | None:
        if value in (None, ""):
            return None
        return Path(value)


class LawRecord(BaseModel):
    title: str
    section_number: str
    content: str


class ParsedLawMetadata(BaseModel):
    source_url: str
    api_url: str
    part: str = "PART X"
    part_title: str = "RULES OF THE ROAD"
    count: int


class ParsedLawCache(BaseModel):
    metadata: ParsedLawMetadata
    laws: list[LawRecord]


class PipelineResult(BaseModel):
    section_number: str
    title: str
    llm_output: dict[str, Any] | list[Any] | None = None
    raw_response: str | None = None
    status: str
    error: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
