from app.core.config import settings


class EmbeddingFactory:
    @staticmethod
    def create():
        provider = settings.EMBEDDINGS_PROVIDER.lower()

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.OPENAI_EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
            )

        if provider == "ollama":
            from langchain_ollama import OllamaEmbeddings

            return OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDINGS_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )

        raise ValueError(f"Unsupported embeddings provider: {settings.EMBEDDINGS_PROVIDER}")
