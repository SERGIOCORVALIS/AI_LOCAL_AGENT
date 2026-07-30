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
