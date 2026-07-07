from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from models import LawRecord, ParsedLawCache, ParsedLawMetadata

DEFAULT_SOURCE_URL = "https://www.ontario.ca/laws/statute/90h08#BK230"
DEFAULT_API_URL = "https://www.ontario.ca/laws/api/v2/legislation/en/doc-search/statute/90h08"

SKIP_CLASS_NAMES = {
    "footnoteLeft",
    "amendments",
    "amendments-heading",
    "Pnote",
    "note",
    "collapsed",
    "toc",
    "tocExpandable",
}


class LawRetrievalError(RuntimeError):
    pass


class LawParseError(RuntimeError):
    pass


def resolve_api_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 3 and path_parts[-2] in {"statute", "loi"}:
        law_type = "statute" if path_parts[-2] == "statute" else "loi"
        code = path_parts[-1]
        lang = "fr" if "lois" in path_parts else "en"
        return f"https://www.ontario.ca/laws/api/v2/legislation/{lang}/doc-search/{law_type}/{code}"
    return DEFAULT_API_URL


def fetch_law_payload(source_url: str, timeout_seconds: float = 60.0) -> dict:
    api_url = resolve_api_url(source_url)
    response = httpx.get(api_url, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), str):
        raise LawRetrievalError("Ontario e-Laws response did not contain a content HTML string.")
    return payload


def load_law_cache(path: str | Path) -> ParsedLawCache | None:
    cache_path = Path(path)
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            return ParsedLawCache.model_validate_json(handle.read())
    except (OSError, ValidationError, json.JSONDecodeError):
        return None


def write_law_cache(path: str | Path, cache: ParsedLawCache) -> None:
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(cache.model_dump_json(indent=2), encoding="utf-8")


def get_or_parse_laws(
    source_url: str,
    parsed_laws_path: str | Path,
    *,
    force_refresh: bool = False,
    timeout_seconds: float = 60.0,
) -> ParsedLawCache:
    if not force_refresh:
        existing = load_law_cache(parsed_laws_path)
        if existing is not None:
            return existing

    api_url = resolve_api_url(source_url)
    payload = fetch_law_payload(source_url, timeout_seconds=timeout_seconds)
    laws = parse_part_x_laws(payload["content"])
    cache = ParsedLawCache(
        metadata=ParsedLawMetadata(
            source_url=source_url,
            api_url=api_url,
            count=len(laws),
        ),
        laws=laws,
    )
    write_law_cache(parsed_laws_path, cache)
    return cache


def parse_part_x_laws(content_html: str) -> list[LawRecord]:
    soup = BeautifulSoup(content_html, "lxml")
    start = _find_part_x_start(soup)
    if start is None:
        raise LawParseError("Could not find Part X, Rules of the Road.")

    elements = list(_iter_part_x_elements(start))
    laws: list[LawRecord] = []
    current_title = ""
    current_section: str | None = None
    current_content: list[str] = []

    pending_title = ""

    for index, element in enumerate(elements):
        if _should_skip_element(element):
            continue
        class_names = _class_names(element)

        if "headnote" in class_names:
            text = _clean_text(element)
            if text:
                next_element = _next_relevant_element(elements[index + 1 :])
                if next_element is not None and _is_numbered_section_start(next_element):
                    pending_title = text
                else:
                    if current_section is None:
                        pending_title = text
                    else:
                        current_content.append(text)
            continue

        if "section" in class_names:
            section_text = _clean_text(element)
            section_number = _extract_section_number(section_text)
            if not section_number:
                if current_section is not None and section_text:
                    current_content.append(section_text)
                    continue
                raise LawParseError(f"Could not extract section number from: {section_text!r}")
            if current_section is not None:
                laws.append(_make_law_record(current_title, current_section, current_content))
            current_title = pending_title
            pending_title = ""
            current_section = section_number
            current_content = [section_text]
            continue

        if current_section is not None:
            text = _clean_text(element)
            if text:
                current_content.append(text)

    if current_section is not None:
        laws.append(_make_law_record(current_title, current_section, current_content))

    return laws


def filter_laws(laws: Iterable[LawRecord], sections: list[str]) -> list[LawRecord]:
    if not sections:
        return list(laws)
    wanted = set(sections)
    return [law for law in laws if law.section_number in wanted]


def _find_part_x_start(soup: BeautifulSoup) -> Tag | None:
    for element in soup.find_all("p", class_="partnum"):
        text = _clean_text(element).upper()
        if "PART X" in text and "RULES OF THE ROAD" in text and "PART X.1" not in text:
            return element
    return None


def _iter_part_x_elements(start: Tag) -> Iterable[Tag]:
    for sibling in start.find_all_next("p"):
        if sibling is start:
            continue
        if "partnum" in _class_names(sibling):
            text = _clean_text(sibling).upper()
            if "PART X.1" in text or ("PART XI" in text and "PART XIV" not in text):
                break
        yield sibling


def _class_names(element: Tag) -> set[str]:
    classes = element.get("class") or []
    return {str(item) for item in classes}


def _should_skip_element(element: Tag) -> bool:
    classes = _class_names(element)
    if any(name.startswith("Y") for name in classes):
        return True
    if classes.intersection(SKIP_CLASS_NAMES):
        return True
    return False


def _next_relevant_element(elements: list[Tag]) -> Tag | None:
    for element in elements:
        if not _should_skip_element(element):
            return element
    return None


def _is_numbered_section_start(element: Tag) -> bool:
    return "section" in _class_names(element) and _extract_section_number(_clean_text(element)) is not None


def _clean_text(element: Tag) -> str:
    text = element.get_text(" ", strip=True)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _extract_section_number(section_text: str) -> str | None:
    match = re.match(r"^(\d+(?:\.\d+)*)\b", section_text)
    return match.group(1) if match else None


def _make_law_record(title: str, section_number: str, content: list[str]) -> LawRecord:
    return LawRecord(
        title=title.strip(),
        section_number=section_number,
        content="\n".join(part for part in content if part).strip(),
    )
