from langchain_community.vectorstores import Chroma

from app.core.config import settings


class VectorStoreFactory:
    @staticmethod
    def create(*, embedding_function, persist_directory: str):
        vector_store_type = settings.VECTOR_STORE_TYPE.lower()

        if vector_store_type == "chroma":
            return Chroma(
                persist_directory=persist_directory,
                embedding_function=embedding_function,
            )

        raise ValueError(f"Unsupported vector store type: {settings.VECTOR_STORE_TYPE}")
