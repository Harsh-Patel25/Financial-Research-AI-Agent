import os
import uuid
import logging
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

from app.ai.interfaces.vector_store import VectorStoreInterface

logger = logging.getLogger(__name__)

PINECONE_INDEX_NAME = "financial-kb"
EMBEDDING_DIMENSION = 1536   # matches text-embedding-3-small


class PineconeVectorStoreImpl(VectorStoreInterface):
    """
    Managed cloud vector store backed by Pinecone (raw SDK, no langchain-pinecone).
    Shared across the whole team — all members read/write the same index
    as long as they share the Pinecone_Vector_Database key from .env.

    Score note: Pinecone cosine similarity is in [0, 1] where HIGHER = more similar.
    This is opposite to ChromaDB's L2 distances (lower = better).
    """

    def __init__(self):
        api_key = os.getenv("Pinecone_Vector_Database")
        if not api_key:
            raise ValueError(
                "Pinecone_Vector_Database is not set in .env. "
                "Get your key from https://app.pinecone.io"
            )

        # Pinecone client (v3+ SDK)
        self._pc = Pinecone(api_key=api_key)

        # Auto-create the index if it doesn't exist yet
        existing = [idx.name for idx in self._pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            logger.info("Creating Pinecone index '%s' …", PINECONE_INDEX_NAME)
            self._pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info("Index '%s' created.", PINECONE_INDEX_NAME)
        else:
            logger.info("Using existing Pinecone index '%s'.", PINECONE_INDEX_NAME)

        self._index = self._pc.Index(PINECONE_INDEX_NAME)

        # Same embedding model as ChromaDB impl — keeps vectors compatible
        self._embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        logger.info("PineconeVectorStoreImpl ready (index: %s)", PINECONE_INDEX_NAME)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self._embeddings.embed_documents(texts)

    def _embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)

    # ── VectorStoreInterface ─────────────────────────────────────────────────

    def add_documents(self, documents: List[Document]) -> None:
        if not documents:
            logger.warning("No documents provided to add_documents")
            return

        texts = [doc.page_content for doc in documents]
        vectors = self._embed_texts(texts)

        # Build Pinecone upsert payload
        records = []
        for doc, vec in zip(documents, vectors):
            records.append({
                "id": str(uuid.uuid4()),
                "values": vec,
                "metadata": {
                    **doc.metadata,
                    "_text": doc.page_content,   # store original text for retrieval
                },
            })

        # Upsert in batches of 100 (Pinecone limit per request)
        batch_size = 100
        for i in range(0, len(records), batch_size):
            self._index.upsert(vectors=records[i : i + batch_size])

        logger.info("Added %d documents to Pinecone.", len(documents))

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: dict = None,
        score_threshold: float = None,
    ) -> List[Tuple[Document, float]]:

        logger.info(
            "Pinecone search | query='%s' | top_k=%d | filter=%s", query, k, filter
        )
        query_vector = self._embed_query(query)

        response = self._index.query(
            vector=query_vector,
            top_k=k,
            filter=filter,
            include_metadata=True,
        )

        results: List[Tuple[Document, float]] = []
        for match in response.get("matches", []):
            meta = match.get("metadata", {})
            text = meta.pop("_text", "")   # extract stored text, clean metadata
            score = match["score"]

            if score_threshold is not None and score < score_threshold:
                continue   # cosine sim: keep >= threshold

            doc = Document(page_content=text, metadata=meta)
            results.append((doc, score))

        logger.info("Pinecone returned %d results.", len(results))
        return results
