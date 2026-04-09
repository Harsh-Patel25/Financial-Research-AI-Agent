import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
import logging
from ..ai.document_loader import DocumentProcessor
from ..ai.vector_store_chroma import ChromaVectorStore

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = logging.getLogger("rag")

# Initialize components
doc_processor = DocumentProcessor()
# Because we built an abstraction, we could swap ChromaVectorStore for QdrantVectorStore here easily.
_vector_store_instance = None

def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = ChromaVectorStore()
    return _vector_store_instance

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a document (PDF/TXT), parses it, splits it, and adds it to the Vector Store.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.txt', '.md', '.csv']:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, TXT, MD, or CSV.")

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        logger.info("Processing uploaded document: %s", file.filename)
        # Parse and split
        chunks = doc_processor.load_and_split(temp_path)
        
        # Add metadata to chunks to remember origin
        for chunk in chunks:
            if not isinstance(chunk.metadata, dict):
                chunk.metadata = {}
            chunk.metadata['source_file'] = file.filename

        # Add to vector store via abstracted interface
        get_vector_store().add_documents(chunks)
        
        # Clean up temp file
        os.remove(temp_path)

        return {
            "status": "success", 
            "message": f"Successfully loaded and embedded document '{file.filename}'", 
            "chunks_added": len(chunks)
        }
    
    except Exception as e:
        logger.error("Failed to upload document: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@router.get("/query")
async def query_documents(q: str, score_threshold: float = 1.5, source_file: str = None):
    """
    Semantic search over the embedded documents.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")
        
    try:
        filter_dict = None
        if source_file:
            # ChromaDB filters on metadata
            filter_dict = {"source_file": source_file}
            
        results = get_vector_store().similarity_search_with_score(
            q, 
            k=4, 
            filter=filter_dict, 
            score_threshold=score_threshold
        )
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        return {"query": q, "results": formatted_results}
    except Exception as e:
        logger.error("Failed to query documents: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
