from app.core.config import settings


class ChatModelFactory:
    @staticmethod
    def create(
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
    ):
        provider = settings.CHAT_PROVIDER.lower()
        effective_temperature = (
            settings.CHAT_TEMPERATURE if temperature is None else temperature
        )

        if provider == "ollama":
            from langchain_ollama import ChatOllama

            kwargs = {
                "model": settings.OLLAMA_MODEL,
                "temperature": effective_temperature,
                "base_url": settings.OLLAMA_BASE_URL,
            }
            if top_p is not None:
                kwargs["top_p"] = top_p
            if top_k is not None:
                kwargs["top_k"] = top_k
            if max_tokens is not None:
                kwargs["num_predict"] = max_tokens
            return ChatOllama(**kwargs)

        if provider in {"openai", "openai_compatible"}:
            from langchain_openai import ChatOpenAI

            kwargs = {
                "model": settings.CHAT_MODEL,
                "temperature": effective_temperature,
                "openai_api_key": settings.OPENAI_API_KEY or "sk-placeholder",
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if top_p is not None:
                kwargs["top_p"] = top_p
            if settings.OPENAI_API_BASE:
                kwargs["openai_api_base"] = settings.OPENAI_API_BASE

            return ChatOpenAI(**kwargs)

        raise ValueError(f"Unsupported chat provider: {settings.CHAT_PROVIDER}")
