import os
from typing import List, Tuple
import logging
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from app.ai.interfaces.vector_store import VectorStoreInterface

logger = logging.getLogger(__name__)

class ChromaVectorStore(VectorStoreInterface):
    def __init__(self, collection_name: str = "financial_knowledge_base", version: str = "v1", persist_directory: str = "./vector_db"):
        self.version = version
        # Versioning: Append version to collection name to implement collection and embedding version control
        self.collection_name = f"{collection_name}_{self.version}"
        self.persist_directory = persist_directory
        
        # Ensure directory exists
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory)
            logger.info("Created vector store persistence directory: %s", self.persist_directory)

        # Initialize Embedding model (using small model for cost efficiency)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Initialize Chroma instance
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
        logger.info("Initialized ChromaVectorStore (Collection: %s)", self.collection_name)

    def add_documents(self, documents: List[Document]) -> None:
        if not documents:
            logger.warning("No documents provided to add_documents")
            return
            
        logger.info("Adding %d documents to vector store", len(documents))
        self.vectorstore.add_documents(documents)
        # Note: In newer versions of langchain-chroma, persistence is handled automatically, 
        # but for langchain_community Chroma, sometimes calling persist is needed if available.
        if hasattr(self.vectorstore, 'persist'):
            self.vectorstore.persist()
            
        logger.info("Documents added successfully")

    def similarity_search_with_score(self, query: str, k: int = 4, filter: dict = None, score_threshold: float = None) -> List[Tuple[Document, float]]:
        logger.info("Performing similarity search | query='%s' | top_k=%d | filter=%s", query, k, filter)
        results = self.vectorstore.similarity_search_with_score(query, k=k, filter=filter)
        
        # In Chroma, LangChain returns distances where lower score is better (L2 distance).
        if score_threshold is not None:
            filtered_results = [(doc, score) for doc, score in results if score <= score_threshold]
            logger.info("Applied score threshold | original_count=%d | filtered_count=%d", len(results), len(filtered_results))
            return filtered_results
            
        return results
