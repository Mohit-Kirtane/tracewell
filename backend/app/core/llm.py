from functools import lru_cache

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def _build_llm(api_key: str) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        temperature=0.0,
    )


@lru_cache
def get_llm() -> Runnable:
    settings = get_settings()
    primary = _build_llm(settings.llm_api_key)
    if not settings.llm_api_key_fallback:
        return primary
    fallback = _build_llm(settings.llm_api_key_fallback)
    return primary.with_fallbacks([fallback])
