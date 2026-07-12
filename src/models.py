from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class TranslatedQuestion(BaseModel):
    id: str
    type: Literal["condition", "action"]
    text: str = Field(min_length=1)

    model_config = ConfigDict(extra="ignore")

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: Any) -> str:
        return str(value).lower()

    @model_validator(mode="after")
    def validate_id(self) -> "TranslatedQuestion":
        expected_prefix = "C" if self.type == "condition" else "A"
        if not self.id.startswith(expected_prefix) or not self.id[1:].isdigit():
            raise ValueError(f"{self.type} question ID must use {expected_prefix}<number>")
        return self


class TranslatedLawOutput(BaseModel):
    law_id: str = Field(min_length=1)
    questions: list[TranslatedQuestion] = Field(min_length=1)

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def validate_questions(self) -> "TranslatedLawOutput":
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question IDs must be unique within a statute")
        return self


class MonitorStatute(BaseModel):
    id: str
    article: str | None
    jurisdiction: Literal["Ontario"] = "Ontario"
    name: str
    statute_text: str
    sub_questions: list[TranslatedQuestion]


class StatuteCatalog(BaseModel):
    version: Literal["1.0"] = "1.0"
    description: str = "Ontario Highway Traffic Act statutes translated into condition/action sub-questions."
    statutes: list[MonitorStatute] = Field(min_length=1)


class PipelineIssue(BaseModel):
    section_number: str
    title: str
    error: str


class PipelineRunResult(BaseModel):
    catalog: StatuteCatalog
    issues: list[PipelineIssue] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
