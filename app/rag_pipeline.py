import os
from typing import List, Dict, Any
from langchain_aws import ChatBedrockConverse, BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from app.telemetry import record_llm_metrics, track_latency

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
CHAT_MODEL_ID = os.getenv("BEDROCK_CHAT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")

SYSTEM_PROMPT = """You are an enterprise AI assistant. Answer the user's question ONLY using the provided context below.
If the answer is not explicitly contained in the context, respond with: "I do not have enough information in the provided documents to answer that."
Always cite the source document name in square brackets, e.g., [policy.md].

Context:
{context}
"""

class EnterpriseRAGService:
    def __init__(self) -> None:
        self.embeddings = BedrockEmbeddings(region_name=AWS_REGION, model_id=EMBED_MODEL_ID)
        self.llm = ChatBedrockConverse(region_name=AWS_REGION, model=CHAT_MODEL_ID, temperature=0.0, max_tokens=1024)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        self.vector_store: FAISS | None = None

    def ingest_text(self, source_name: str, text: str) -> int:
        raw_doc = Document(page_content=text, metadata={"source": source_name})
        chunks = self.splitter.split_documents([raw_doc])
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vector_store.add_documents(chunks)
        return len(chunks)

    def query(self, question: str, k: int = 3) -> Dict[str, Any]:
        if self.vector_store is None:
            return {"answer": "No documents have been ingested yet. Call POST /ingest first.", "citations": [], "retrieved_contexts": [], "usage": {}}

        results = self.vector_store.similarity_search_with_score(question, k=k)
        context_blocks, raw_contexts, citations = [], [], []

        for doc, distance in results:
            src = doc.metadata.get("source", "unknown")
            context_blocks.append(f"[{src}]\n{doc.page_content}")
            raw_contexts.append(doc.page_content)
            citations.append({"source": src, "distance": round(float(distance), 4)})

        prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])
        chain = prompt | self.llm

        with track_latency() as timer:
            response = chain.invoke({"context": "\n\n---\n\n".join(context_blocks), "question": question})

        usage_meta = getattr(response, "usage_metadata", {}) or {}
        in_tokens = usage_meta.get("input_tokens", 0)
        out_tokens = usage_meta.get("output_tokens", 0)
        top_score = citations[0]["distance"] if citations else None

        record_llm_metrics(CHAT_MODEL_ID, "/query", in_tokens, out_tokens, timer["elapsed_ms"], top_score)

        return {
            "answer": response.content,
            "citations": citations,
            "retrieved_contexts": raw_contexts,
            "usage": {"input_tokens": in_tokens, "output_tokens": out_tokens, "latency_ms": round(timer["elapsed_ms"], 2)},
        }
