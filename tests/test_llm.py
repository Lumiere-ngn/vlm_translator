import httpx
import pytest
import respx

from vlm_translator.llm import LLMResponseError, call_llama_cpp
from vlm_translator.models import LLMConfig


def _config() -> LLMConfig:
    return LLMConfig(base_url="http://llama.test/v1/chat/completions", model="test")


@respx.mock
def test_call_llama_cpp_valid_json():
    respx.post("http://llama.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    )

    parsed, raw = call_llama_cpp("prompt", _config(), retries=0, timeout_seconds=10)

    assert parsed == {"ok": True}
    assert raw == '{"ok": true}'


@respx.mock
def test_call_llama_cpp_retries_invalid_json_then_succeeds():
    route = respx.post("http://llama.test/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]}),
            httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}]}),
        ]
    )

    parsed, _ = call_llama_cpp("prompt", _config(), retries=1, timeout_seconds=10)

    assert parsed == {"ok": True}
    assert route.call_count == 2


@respx.mock
def test_call_llama_cpp_invalid_json_raises_after_retries():
    respx.post("http://llama.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]})
    )

    with pytest.raises(LLMResponseError):
        call_llama_cpp("prompt", _config(), retries=0, timeout_seconds=10)

