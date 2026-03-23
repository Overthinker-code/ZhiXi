from app.core.config import settings


class ChatModelFactory:
    @staticmethod
    def create():
        provider = settings.CHAT_PROVIDER.lower()

        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                temperature=settings.CHAT_TEMPERATURE,
                base_url=settings.OLLAMA_BASE_URL,
            )

        if provider in {"openai", "openai_compatible"}:
            from langchain_openai import ChatOpenAI

            kwargs = {
                "model": settings.CHAT_MODEL,
                "temperature": settings.CHAT_TEMPERATURE,
                "openai_api_key": settings.OPENAI_API_KEY or "sk-placeholder",
            }
            if settings.OPENAI_API_BASE:
                kwargs["openai_api_base"] = settings.OPENAI_API_BASE

            return ChatOpenAI(**kwargs)

        raise ValueError(f"Unsupported chat provider: {settings.CHAT_PROVIDER}")
