from pathlib import Path
from unittest.mock import MagicMock, patch

from services.llm import OLLAMA_UNAVAILABLE, OllamaClient
from services.perception import CodeIntelligence, VisionAnalyzer, WebParser
from services.perception.web import parse_duckduckgo_html


def test_web_parser_extracts_title_and_links() -> None:
    document = WebParser().parse_html(
        "https://example.com",
        (
            "<html><head><title>Example</title></head>"
            "<body><p>Hello</p><a href='/docs'>Docs</a></body></html>"
        ),
    )
    assert document.title == "Example"
    assert "Hello" in document.markdown
    assert "https://example.com/docs" in document.links


def test_parse_duckduckgo_html_results() -> None:
    html = """
    <html><body>
      <div class="result results_links web-result">
        <h2 class="result__title">
          <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs">
            Example Docs
          </a>
        </h2>
        <a class="result__snippet" href="#">Useful documentation snippet</a>
      </div>
      <div class="result results_links web-result result--ad">
        <h2 class="result__title">
          <a class="result__a" href="https://ads.example">Ad</a>
        </h2>
      </div>
      <div class="result results_links web-result">
        <h2 class="result__title">
          <a class="result__a" href="https://second.example/page">Second Hit</a>
        </h2>
        <td class="result__snippet">Another snippet</td>
      </div>
    </body></html>
    """
    results = parse_duckduckgo_html(html, max_results=5)
    assert len(results) == 2
    assert results[0].title == "Example Docs"
    assert results[0].url == "https://example.com/docs"
    assert "Useful documentation" in results[0].snippet
    assert results[1].url == "https://second.example/page"


def test_web_parser_search_uses_ddg_endpoint() -> None:
    client = MagicMock()
    client.post.return_value = MagicMock(
        text=(
            '<div class="result web-result">'
            '<a class="result__a" href="https://example.com">Title</a>'
            '<a class="result__snippet">Snippet</a></div>'
        ),
        raise_for_status=MagicMock(),
    )
    response = WebParser(client=client).search("local agents", max_results=3)
    assert response.provider == "duckduckgo"
    assert response.query == "local agents"
    assert response.results[0].url == "https://example.com"
    client.post.assert_called_once()
    assert client.post.call_args.args[0] == "https://html.duckduckgo.com/html/"


def test_vision_analyzer_reads_png_dimensions(tmp_path: Path) -> None:
    # Minimal valid PNG header + IHDR width/height = 2x3
    png = bytearray(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x02"
        b"\x00\x00\x00\x03"
        b"\x08\x02\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(bytes(png))
    analysis = VisionAnalyzer().inspect_image(image_path)
    assert analysis.width == 2
    assert analysis.height == 3
    assert "format=png" in analysis.summary


def test_vision_analyzer_uses_ollama_vlm(tmp_path: Path) -> None:
    png = bytearray(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x02"
        b"\x00\x00\x00\x03"
        b"\x08\x02\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )
    image_path = tmp_path / "ui.png"
    image_path.write_bytes(bytes(png))
    client = MagicMock(spec=OllamaClient)
    client.generate_with_image.return_value = "button labeled Save"
    analysis = VisionAnalyzer(ollama_client=client, vision_model="vision-model").inspect_image(
        image_path
    )
    assert "vlm=button labeled Save" in analysis.summary
    assert "vlm" in analysis.labels
    client.generate_with_image.assert_called_once()


def test_vision_analyzer_marks_unavailable_vlm(tmp_path: Path) -> None:
    png = bytearray(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01"
        b"\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )
    image_path = tmp_path / "tiny.png"
    image_path.write_bytes(bytes(png))
    client = MagicMock(spec=OllamaClient)
    client.generate_with_image.return_value = OLLAMA_UNAVAILABLE
    analysis = VisionAnalyzer(ollama_client=client).inspect_image(image_path)
    assert OLLAMA_UNAVAILABLE in analysis.summary


def test_vision_analyzer_ocr_and_formats(tmp_path: Path) -> None:
    gif = tmp_path / "anim.gif"
    gif.write_bytes(b"GIF89a" + b"\x04\x00\x05\x00" + b"\x00" * 4)
    analysis = VisionAnalyzer().inspect_image(gif)
    assert analysis.width == 4
    assert analysis.height == 5
    assert "format=gif" in analysis.summary

    jpeg = tmp_path / "photo.jpg"
    # SOI + SOF0 marker with 10x20 dimensions
    jpeg.write_bytes(
        b"\xff\xd8\xff\xc0\x00\x11\x08\x00\x0a\x00\x14\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    )
    jpeg_analysis = VisionAnalyzer().inspect_image(jpeg)
    assert jpeg_analysis.width == 20
    assert jpeg_analysis.height == 10

    missing = tmp_path / "missing.png"
    try:
        VisionAnalyzer().inspect_image(missing)
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass

    png = tmp_path / "ocr.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x05\x00"
        b"\x00\x00\x04\x00"
        b"\x08\x02\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )
    fake_pytesseract = MagicMock()
    fake_pytesseract.get_tesseract_version.return_value = "5"
    fake_pytesseract.image_to_string.return_value = "Hello OCR"
    fake_image = MagicMock()
    with (
        patch("services.perception.vision.find_spec", return_value=object()),
        patch.dict(
            "sys.modules",
            {
                "pytesseract": fake_pytesseract,
                "PIL": MagicMock(),
                "PIL.Image": MagicMock(open=MagicMock(return_value=fake_image)),
            },
        ),
    ):
        ocr_analysis = VisionAnalyzer().inspect_image(png)
    assert "ocr=Hello OCR" in ocr_analysis.summary
    assert VisionAnalyzer.ocr_available() in {True, False}


def test_stt_backend_helpers(tmp_path: Path) -> None:
    from services.perception.stt import STT_UNAVAILABLE, SpeechToText

    stt = SpeechToText()
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")

    with patch("services.perception.stt.find_spec", return_value=None):
        assert stt._transcribe_faster_whisper(audio, "en") is None
        assert stt._transcribe_openai_whisper(audio, "en") is None

    fake_segment = MagicMock()
    fake_segment.text = " hi "
    fake_model = MagicMock()
    fake_model.transcribe.return_value = ([fake_segment], None)
    fake_fw = MagicMock()
    fake_fw.WhisperModel.return_value = fake_model
    with (
        patch("services.perception.stt.find_spec", return_value=object()),
        patch.dict("sys.modules", {"faster_whisper": fake_fw}),
    ):
        assert stt._transcribe_faster_whisper(audio, "en") == "hi"

    fake_whisper = MagicMock()
    fake_whisper.load_model.return_value.transcribe.return_value = {"text": "open"}
    with (
        patch(
            "services.perception.stt.find_spec",
            side_effect=lambda name: object() if name == "whisper" else None,
        ),
        patch.dict("sys.modules", {"whisper": fake_whisper}),
    ):
        assert stt._transcribe_openai_whisper(audio, "en") == "open"

    with (
        patch.object(stt, "_transcribe_faster_whisper", return_value=None),
        patch.object(stt, "_transcribe_openai_whisper", return_value=None),
    ):
        assert stt.transcribe(audio) == STT_UNAVAILABLE


def test_code_intelligence_indexes_python_tree(tmp_path: Path) -> None:
    module_path = tmp_path / "sample.py"
    module_path.write_text(
        "import json\nfrom pathlib import Path\n\ndef run() -> None:\n    json.dumps({})\n",
        encoding="utf-8",
    )
    summary = CodeIntelligence().index_python_tree(tmp_path)
    assert str(module_path) in summary.python_files
    assert "json" in summary.import_edges[str(module_path)]
    assert "function:run" in summary.symbols[str(module_path)]
    assert "json.dumps" in summary.call_edges[str(module_path)]
