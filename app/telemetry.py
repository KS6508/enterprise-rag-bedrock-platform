import os
import time
import logging
from contextlib import contextmanager
from datadog import statsd

logger = logging.getLogger("rag.telemetry")
ENV_NAME = os.getenv("ENVIRONMENT", "dev")

def record_llm_metrics(model_id: str, endpoint: str, input_tokens: int, output_tokens: int, latency_ms: float, top_similarity: float | None = None) -> None:
    tags = [f"model:{model_id}", f"endpoint:{endpoint}", f"env:{ENV_NAME}"]
    try:
        statsd.increment("llm.tokens.input", value=input_tokens, tags=tags)
        statsd.increment("llm.tokens.output", value=output_tokens, tags=tags)
        statsd.histogram("llm.latency.ms", value=latency_ms, tags=tags)
        if top_similarity is not None:
            statsd.gauge("rag.retrieval.top_similarity", value=top_similarity, tags=tags)
    except Exception as exc:
        logger.debug("Datadog statsd emission skipped: %s", exc)

@contextmanager
def track_latency():
    start = time.perf_counter()
    timing = {"elapsed_ms": 0.0}
    try:
        yield timing
    finally:
        timing["elapsed_ms"] = (time.perf_counter() - start) * 1000.0
