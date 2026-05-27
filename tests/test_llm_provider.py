from src.llm.mock_provider import MockProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.provider import LLMProvider
from src.llm.replay_provider import ReplayProvider


def test_llm_provider_stubs_exist():
    assert issubclass(MockProvider, LLMProvider)
    assert issubclass(ReplayProvider, LLMProvider)
    assert issubclass(OpenAIProvider, LLMProvider)
    assert MockProvider().extract_mistakes()["mistakes"]
