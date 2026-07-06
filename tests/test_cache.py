import pytest

from vlm_translator.models import LawRecord, ParsedLawCache, ParsedLawMetadata
from vlm_translator.ontario_laws import get_or_parse_laws, load_law_cache, write_law_cache


def test_load_law_cache_returns_none_for_invalid_cache(tmp_path):
    cache_path = tmp_path / "laws.json"
    cache_path.write_text("not json", encoding="utf-8")

    assert load_law_cache(cache_path) is None


def test_get_or_parse_laws_reuses_valid_cache(monkeypatch, tmp_path):
    cache_path = tmp_path / "laws.json"
    cache = ParsedLawCache(
        metadata=ParsedLawMetadata(
            source_url="source",
            api_url="api",
            count=1,
        ),
        laws=[LawRecord(title="Title", section_number="133", content="Content")],
    )
    write_law_cache(cache_path, cache)

    def fail_fetch(*args, **kwargs):
        raise AssertionError("fetch should not be called")

    monkeypatch.setattr("vlm_translator.ontario_laws.fetch_law_payload", fail_fetch)

    loaded = get_or_parse_laws("source", cache_path)

    assert loaded.laws[0].section_number == "133"


def test_get_or_parse_laws_force_refresh_fetches(monkeypatch, tmp_path):
    cache_path = tmp_path / "laws.json"

    monkeypatch.setattr(
        "vlm_translator.ontario_laws.fetch_law_payload",
        lambda *args, **kwargs: {
            "content": """
            <p class="partnum">PART X <br> RULES OF THE ROAD</p>
            <p class="headnote">Title</p>
            <p class="section"><b>133 </b>Content</p>
            <p class="partnum">PART X.1 <br> TOLL HIGHWAYS</p>
            """
        },
    )

    loaded = get_or_parse_laws("source", cache_path, force_refresh=True)

    assert loaded.laws[0].section_number == "133"
    assert load_law_cache(cache_path) is not None

