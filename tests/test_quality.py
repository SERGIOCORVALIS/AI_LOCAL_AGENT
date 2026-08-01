from pathlib import Path
from unittest.mock import MagicMock

from services.memory.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingService,
    embed_text,
    resize_vector,
)
from services.quality import QualityEvaluator


def test_quality_evaluator_reports_release_readiness() -> None:
    def runner(command: list[str], cwd: Path, timeout: float) -> tuple[int, str, str]:
        del cwd, timeout
        tool = " ".join(command)
        if "ruff" in tool:
            return 0, "All checks passed!", ""
        if "mypy" in tool:
            return 0, "Success: no issues found", ""
        if "pytest" in tool:
            return 0, "5 passed", ""
        return 1, "", "unknown"

    report = QualityEvaluator(runner=runner).evaluate(project_root=Path("."))
    assert report.lint_ready is True
    assert report.typed_contracts_ready is True
    assert report.tests_ready is True
    assert report.details["tests_dir_present"] is True
    assert report.details["ruff_exit_code"] == 0


def test_quality_evaluator_presence_only_skips_tools() -> None:
    report = QualityEvaluator(runner=MagicMock()).evaluate(run_tools=False)
    assert report.lint_ready is False
    assert report.tests_ready is False
    assert report.details["tests_dir_present"] is True


def test_embed_text_is_deterministic_and_normalized() -> None:
    left = embed_text("strict typing preference")
    right = embed_text("strict typing preference")
    other = embed_text("totally different memory")
    assert left == right
    assert len(left) == EMBEDDING_DIMENSION
    assert left != other
    norm = sum(value * value for value in left) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_embedding_service_uses_ollama_when_available() -> None:
    client = MagicMock()
    client.ping.return_value = True
    client.embed.return_value = [0.5] * 128
    service = EmbeddingService(ollama_client=client, model="nomic-embed-text")
    vector = service.embed("semantic memory")
    assert len(vector) == 128
    assert service.dimensions == 128
    assert service.backend == "ollama"
    assert abs(sum(value * value for value in vector) ** 0.5 - 1.0) < 1e-6
    client.embed.assert_called_once()


def test_embedding_service_can_force_fixed_dimensions() -> None:
    client = MagicMock()
    client.ping.return_value = True
    client.embed.return_value = [0.5] * 128
    service = EmbeddingService(
        ollama_client=client,
        model="nomic-embed-text",
        dimensions=64,
        prefer_native=False,
    )
    vector = service.embed("semantic memory")
    assert len(vector) == 64


def test_resize_vector_pads_and_buckets() -> None:
    assert len(resize_vector([1.0, 0.0], 4)) == 4
    assert len(resize_vector([1.0] * 10, 4)) == 4
