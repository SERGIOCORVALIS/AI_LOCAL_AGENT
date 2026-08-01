from pathlib import Path

from services.fs_daemon import FileSystemDaemon


def test_fs_daemon_scans_and_proposes_routes(tmp_path: Path) -> None:
    (tmp_path / "Invoice 001.pdf").write_text("pdf payload", encoding="utf-8")
    (tmp_path / "script.py").write_text("print('ok')", encoding="utf-8")

    daemon = FileSystemDaemon()
    records = daemon.scan_directory(tmp_path)
    proposals = daemon.propose_routes(records)

    assert len(records) == 2
    assert any(record.category == "documents" for record in records)
    assert any(proposal.dry_run_only for proposal in proposals)


def test_fs_daemon_applies_routes(tmp_path: Path) -> None:
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "notes.txt"
    file_path.write_text("hello", encoding="utf-8")

    daemon = FileSystemDaemon()
    proposals = daemon.propose_routes(daemon.scan_directory(source))
    moved = daemon.apply_routes(proposals, tmp_path / "organized")

    assert len(moved) == 1
    assert moved[0].exists()
    assert not file_path.exists()
    assert proposals[0].dry_run_only is False
