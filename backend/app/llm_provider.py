"""Compatibility exports; implementation lives in app.generations.adapters.llm."""

# Keep legacy loader monkeypatches attached to the implementation module.
import sys

from app.generations.adapters import llm as _implementation
from app.generations.adapters.llm import Completion as Completion
from app.generations.adapters.llm import LLMGenerator as LLMGenerator
from app.generations.adapters.llm import load_completion as load_completion
from app.generations.adapters.llm import logger as logger
from app.generations.adapters.llm import output_schema as output_schema
from app.generations.adapters.llm import translate_error as translate_error

sys.modules[__name__] = _implementation
