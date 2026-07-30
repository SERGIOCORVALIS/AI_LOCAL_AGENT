from __future__ import annotations

import hashlib
from pathlib import Path

from packages.fs import FileRecord, FileRouteProposal


class FileSystemDaemon:
    """Dry-run file intake scanner for Windows-first housekeeping."""

    def scan_directory(self, root: Path) -> list[FileRecord]:
        records: list[FileRecord] = []
        for path in root.iterdir():
            if path.is_file():
                records.append(self._record_for(path))
        return records

    def propose_routes(self, records: list[FileRecord]) -> list[FileRouteProposal]:
        proposals: list[FileRouteProposal] = []
        for record in records:
            proposals.append(
                FileRouteProposal(
                    source_path=record.path,
                    suggested_name=self._suggest_name(record),
                    target_bucket=record.category,
                    reasons=[f"classified as {record.category}", "dry-run proposal only"],
                )
            )
        return proposals

    def _record_for(self, path: Path) -> FileRecord:
        payload = path.read_bytes()
        return FileRecord(
            path=str(path),
            suffix=path.suffix.lower(),
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            category=self._classify(path.suffix.lower()),
        )

    def _classify(self, suffix: str) -> str:
        if suffix in {".pdf"}:
            return "documents"
        if suffix in {".zip", ".7z", ".rar"}:
            return "archives"
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            return "images"
        if suffix in {".py", ".ts", ".tsx", ".rs"}:
            return "code"
        return "inbox"

    def _suggest_name(self, record: FileRecord) -> str:
        stem = Path(record.path).stem.replace(" ", "_").lower()
        return f"{record.category}_{stem}{record.suffix}"
