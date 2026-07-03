"""LangChain callback handler (FR-9 #2).

Attaches via LangChain's official callback mechanism — the user's chain is
never modified, blocked, or delayed (passive observer). Requires
`langchain-core` (optional dependency): pip install castor[langchain].
"""
from __future__ import annotations

from typing import Any

from ..observer import CastorObserver

try:
    from langchain_core.callbacks import BaseCallbackHandler

    _LANGCHAIN_AVAILABLE = True
except ImportError:  # langchain not installed — class stays importable, unusable
    BaseCallbackHandler = object
    _LANGCHAIN_AVAILABLE = False


class CastorCallbackHandler(BaseCallbackHandler):
    """Feed LLM / chain / tool outputs into a CastorObserver (FR-9).

    Usage::

        handler = CastorCallbackHandler()
        chain.invoke(inputs, config={"callbacks": [handler]})
        report = handler.observer.report()
    """

    def __init__(self, observer: CastorObserver | None = None) -> None:
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-core is required for CastorCallbackHandler: "
                "pip install langchain-core"
            )
        super().__init__()
        self.observer = observer if observer is not None else CastorObserver()
        self._counter = 0

    def _observe(self, text: str, role: str, name: str | None = None) -> None:
        self._counter += 1
        self.observer.observe(
            {
                "step_id": self._counter,
                "text": text,
                "agent_name": name,
                "role": role,
            }
        )

    # --- LangChain callback surface (passive: record outputs only) ---

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        try:
            generations = getattr(response, "generations", None) or []
            texts = [g.text for batch in generations for g in batch if getattr(g, "text", "")]
            if texts:
                self._observe(" ".join(texts), role="llm", name=kwargs.get("name"))
        except Exception:  # FR-12: never break the user's chain
            pass

    def on_chain_end(self, outputs: Any, **kwargs: Any) -> None:
        try:
            if isinstance(outputs, dict):
                text = " ".join(str(v) for v in outputs.values() if isinstance(v, str))
            else:
                text = str(outputs)
            if text.strip():
                self._observe(text, role="chain", name=kwargs.get("name"))
        except Exception:  # FR-12
            pass

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        try:
            text = str(output)
            if text.strip():
                self._observe(text, role="tool", name=kwargs.get("name"))
        except Exception:  # FR-12
            pass
