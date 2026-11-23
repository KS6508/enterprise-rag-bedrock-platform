import json, os
from pathlib import Path
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric
from app.rag_pipeline import EnterpriseRAGService

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"

@pytest.mark.skipif(not os.getenv("RUN_LIVE_EVALS"), reason="Set RUN_LIVE_EVALS=1 with AWS credentials to run live evals.")
def test_rag_faithfulness_and_relevancy():
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    service = EnterpriseRAGService()
    for item in cases:
        service.ingest_text(item["source_name"], item["document_text"])
        result = service.query(item["question"], k=2)
        test_case = LLMTestCase(
            input=item["question"],
            actual_output=result["answer"],
            expected_output=item["expected_output"],
            retrieval_context=result["retrieved_contexts"],
        )
        assert_test(test_case, [FaithfulnessMetric(threshold=0.85), AnswerRelevancyMetric(threshold=0.80)])
