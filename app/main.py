from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.rag_pipeline import EnterpriseRAGService

app = FastAPI(title="Enterprise Bedrock RAG Platform", version="0.1.0")
rag_service = EnterpriseRAGService()

class IngestRequest(BaseModel):
    source_name: str = Field(..., example="security_policy.md")
    content: str = Field(..., min_length=10)

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, example="What is our data retention policy?")
    top_k: int = Field(default=3, ge=1, le=10)

@app.get("/health")
def health_check():
    return {"status": "ok", "index_ready": rag_service.vector_store is not None}

@app.post("/ingest")
def ingest_document(payload: IngestRequest):
    try:
        chunks_created = rag_service.ingest_text(payload.source_name, payload.content)
        return {"status": "ingested", "source": payload.source_name, "chunks": chunks_created}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/query")
def query_rag(payload: QueryRequest):
    try:
        return rag_service.query(payload.question, k=payload.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
