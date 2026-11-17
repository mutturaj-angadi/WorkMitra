"""Make the test suite deterministic and prevent accidental provider calls."""

import os
from pathlib import Path

import pytest

os.environ["LLM_PROVIDER"] = "mock"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

TEST_FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def empty_test_corpus() -> Path:
    return TEST_FIXTURES / "empty"


@pytest.fixture
def gazette_test_corpus() -> Path:
    return TEST_FIXTURES / "legal"
