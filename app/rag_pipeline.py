import os
from typing import List, Dict, Any
from langchain_aws import ChatBedrockConverse, BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from app.telemetry import record_llm_metrics, track_latency

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
CHAT_MODEL_ID = os.getenv("BEDROCK_CHAT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
MOCK_BEDROCK = os.getenv("MOCK_BEDROCK", "0") == "1"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
COLLECTION_NAME = os.getenv("PGVECTOR_COLLECTION", "enterprise_rag_docs")

SYSTEM_PROMPT = """You are an enterprise AI assistant. Answer the user's question ONLY using the provided context below.
If the answer is not explicitly contained in the context, respond with: "I do not have enough information in the provided documents to answer that."
Always cite the source document name in square brackets, e.g., [policy.md].

Context:
{context}
"""


class EnterpriseRAGService:
    def __init__(self) -> None:
        self._embeddings = None
        self._llm = None
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        self.vector_store = None
        self.backend_type = "pgvector" if DATABASE_URL else "faiss"

    @property
    def embeddings(self):
        if self._embeddings is None:
            if MOCK_BEDROCK:
                self._embeddings = FakeEmbeddings(size=1024)
            else:
                self._embeddings = BedrockEmbeddings(region_name=AWS_REGION, model_id=EMBED_MODEL_ID)
        return self._embeddings

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatBedrockConverse(
                region_name=AWS_REGION, model=CHAT_MODEL_ID, temperature=0.0, max_tokens=1024
            )
        return self._llm

    def _get_or_init_store(self, chunks: List[Document] | None = None):
        if self.vector_store is not None:
            if chunks:
                self.vector_store.add_documents(chunks)
            return self.vector_store

        if DATABASE_URL:
            self.vector_store = PGVector(
                embeddings=self.embeddings,
                collection_name=COLLECTION_NAME,
                connection=DATABASE_URL,
                use_jsonb=True,
            )
            if chunks:
                self.vector_store.add_documents(chunks)
        elif chunks:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)

        return self.vector_store

    def ingest_text(self, source_name: str, text: str) -> int:
        raw_doc = Document(page_content=text, metadata={"source": source_name})
        chunks = self.splitter.split_documents([raw_doc])
        self._get_or_init_store(chunks=chunks)
        return len(chunks)

    def query(self, question: str, k: int = 3) -> Dict[str, Any]:
        store = self._get_or_init_store()
        if store is None:
            return {
                "answer": "No documents have been ingested yet. Call POST /ingest first.",
                "citations": [],
                "retrieved_contexts": [],
                "usage": {"vector_backend": self.backend_type},
            }

        results = store.similarity_search_with_score(question, k=k)
        if not results:
            return {
                "answer": "No matching documents found in the vector store. Call POST /ingest first.",
                "citations": [],
                "retrieved_contexts": [],
                "usage": {"vector_backend": self.backend_type},
            }

        context_blocks, raw_contexts, citations = [], [], []

        for doc, distance in results:
            src = doc.metadata.get("source", "unknown")
            context_blocks.append(f"[{src}]\n{doc.page_content}")
            raw_contexts.append(doc.page_content)
            citations.append({"source": src, "distance": round(float(distance), 4)})

        with track_latency() as timer:
            if MOCK_BEDROCK:
                top_src = citations[0]["source"] if citations else "doc"
                answer_text = f"[MOCK MODE] Grounded summary from [{top_src}]: {raw_contexts[0]}"
                in_tokens, out_tokens = 120, 45
            else:
                prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])
                chain = prompt | self.llm
                response = chain.invoke({"context": "\n\n---\n\n".join(context_blocks), "question": question})
                answer_text = response.content
                usage_meta = getattr(response, "usage_metadata", {}) or {}
                in_tokens = usage_meta.get("input_tokens", 0)
                out_tokens = usage_meta.get("output_tokens", 0)

        top_score = citations[0]["distance"] if citations else None
        record_llm_metrics(CHAT_MODEL_ID, "/query", in_tokens, out_tokens, timer["elapsed_ms"], top_score)

        return {
            "answer": answer_text,
            "citations": citations,
            "retrieved_contexts": raw_contexts,
            "usage": {
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
                "latency_ms": round(timer["elapsed_ms"], 2),
                "mock_mode": MOCK_BEDROCK,
                "vector_backend": self.backend_type,
            },
        }
