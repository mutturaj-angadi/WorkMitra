import os

import pytest
from pydantic import ValidationError

from backend.config import Settings, configure_langchain_tracing


def test_unsupported_provider_is_rejected_instead_of_defaulting_to_mock():
    with pytest.raises(ValidationError, match="LLM_PROVIDER"):
        Settings(llm_provider="gemni")


def test_gemini_requires_model_and_key():
    with pytest.raises(ValidationError, match="GOOGLE_API_KEY"):
        Settings(
            llm_provider="gemini", google_api_key="", google_model="gemini-3.8-flash"
        )
    with pytest.raises(ValidationError, match="GOOGLE_MODEL"):
        Settings(llm_provider="gemini", google_api_key="test-key", google_model="")


def test_langchain_tracing_settings_are_exported_for_runtime(monkeypatch):
    for name in (
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT",
    ):
        if name in os.environ:
            monkeypatch.setenv(name, os.environ[name])
        else:
            monkeypatch.delenv(name, raising=False)
    settings = Settings(
        llm_provider="mock",
        langchain_tracing_v2=True,
        langchain_api_key="test-only-key",
        langchain_project="runtime-trace-test",
    )
    configure_langchain_tracing(settings)
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "test-only-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "runtime-trace-test"
