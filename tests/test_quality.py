from services.quality import QualityEvaluator


def test_quality_evaluator_reports_release_readiness() -> None:
    report = QualityEvaluator().evaluate()
    assert report.lint_ready is True
    assert report.tests_ready is True
