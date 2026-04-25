from app.core.config import settings

try:
    from langchain_chroma import Chroma as LangchainChroma
except Exception:
    LangchainChroma = None

try:
    from langchain_community.vectorstores import Chroma as CommunityChroma
except Exception:
    CommunityChroma = None


class VectorStoreFactory:
    @staticmethod
    def create(*, embedding_function, persist_directory: str):
        vector_store_type = settings.VECTOR_STORE_TYPE.lower()

        if vector_store_type == "chroma":
            chroma_cls = LangchainChroma or CommunityChroma
            if chroma_cls is None:
                raise ImportError(
                    "Chroma vector store backend is unavailable. "
                    "Install `langchain-chroma` or ensure `langchain-community` is available."
                )
            return chroma_cls(
                persist_directory=persist_directory,
                embedding_function=embedding_function,
            )

        raise ValueError(f"Unsupported vector store type: {settings.VECTOR_STORE_TYPE}")
