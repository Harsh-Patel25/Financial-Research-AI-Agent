"""
Document loader module for the Financial Research AI Agent.
Handles ingestion of PDFs and Text files and chunks them for vector storage.
"""

import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import structlog

logger = structlog.get_logger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def load_and_split(self, file_path: str) -> List[Document]:
        """Loads a document from the file path and splits it into chunks."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        _, ext = os.path.splitext(file_path.lower())
        loader = None

        if ext == '.pdf':
            logger.info("Loading PDF document", file=file_path)
            loader = PyPDFLoader(file_path)
        elif ext in ['.txt', '.md', '.csv']:
            logger.info("Loading Text document", file=file_path)
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        try:
            docs = loader.load()
            logger.info("Splitting document", num_pages=len(docs))
            chunks = self.text_splitter.split_documents(docs)
            logger.info("Document chunking complete", num_chunks=len(chunks))
            return chunks
        except Exception as e:
            logger.error("Error loading document", error=str(e))
            raise e
