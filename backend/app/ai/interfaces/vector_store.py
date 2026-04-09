from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document

class VectorStoreInterface(ABC):
    """
    Abstract interface for vector database operations.
    This ensures that the underlying vector storage (Chroma, Qdrant, Pinecone, etc.)
    can be easily swapped without modifying the core business logic.
    """

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        """
        Adds a list of Langchain documents to the vector store.
        """
        pass

    @abstractmethod
    def similarity_search_with_score(self, query: str, k: int = 4, filter: dict = None, score_threshold: float = None) -> List[Tuple[Document, float]]:
        """
        Retrieves the top k most similar documents to the query.
        Optionally filters by metadata and drops results worse than the score threshold.
        Returns a list of tuples containing the Document and the similarity score.
        """
        pass
