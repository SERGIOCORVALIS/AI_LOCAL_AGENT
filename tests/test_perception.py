from pathlib import Path

from services.perception import CodeIntelligence, VisionAnalyzer, WebParser


def test_web_parser_extracts_title() -> None:
    document = WebParser().parse_html(
        "https://example.com",
        "<html><head><title>Example</title></head><body><p>Hello</p></body></html>",
    )
    assert document.title == "Example"
    assert "Hello" in document.markdown


def test_vision_analyzer_reads_binary_image(tmp_path: Path) -> None:
    image_path = tmp_path / "screen.bin"
    image_path.write_bytes(b"binary-image")
    analysis = VisionAnalyzer().inspect_image(image_path)
    assert "Binary image captured" in analysis.summary


def test_code_intelligence_indexes_python_tree(tmp_path: Path) -> None:
    module_path = tmp_path / "sample.py"
    module_path.write_text("import json\nfrom pathlib import Path\n", encoding="utf-8")
    summary = CodeIntelligence().index_python_tree(tmp_path)
    assert str(module_path) in summary.python_files
    assert "json" in summary.import_edges[str(module_path)]
