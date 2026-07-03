"""FR-9 #2: LangChain callback handler (uses langchain-core from dev extras)."""
import pytest

pytest.importorskip("langchain_core")

from castor import CastorObserver, ThresholdProfile
from castor.integrations.langchain import CastorCallbackHandler
from tests.conftest import FakeEmbedder, FakeNLI


class FakeGeneration:
    def __init__(self, text):
        self.text = text


class FakeLLMResult:
    def __init__(self, texts):
        self.generations = [[FakeGeneration(t) for t in texts]]


def make_handler():
    observer = CastorObserver(
        embedder=FakeEmbedder(),
        entailment=FakeNLI(),
        profile=ThresholdProfile(name="test", drift_threshold=0.3, aggregate_threshold=0.5),
    )
    return CastorCallbackHandler(observer=observer)


def test_llm_and_tool_outputs_become_steps():
    handler = make_handler()
    handler.on_llm_end(FakeLLMResult(["alpha beta gamma"]))
    handler.on_tool_end("alpha beta delta", name="search")
    handler.on_llm_end(FakeLLMResult(["zulu yankee xray"]))
    report = handler.observer.report()
    assert len(report.steps) == 3
    assert report.verdict


def test_chain_end_dict_outputs():
    handler = make_handler()
    handler.on_chain_end({"answer": "alpha beta gamma", "score": 3})
    report = handler.observer.report()
    assert len(report.steps) == 1


def test_malformed_events_never_raise():
    handler = make_handler()
    handler.on_llm_end(None)
    handler.on_chain_end(object())
    handler.on_tool_end("")
    # No steps recorded from garbage, no exception either (FR-12).
    report = handler.observer.report()
    assert report.monitoring_failure is None
