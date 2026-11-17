"""Make the test suite deterministic and prevent accidental provider calls."""

import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
