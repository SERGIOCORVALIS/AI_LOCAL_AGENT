from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from packages.fs import FileRecord, FileRouteProposal


class FileSystemDaemon:
    """Recursive Windows-first file intake scanner with dry-run and apply modes."""

    def scan_directory(self, root: Path, *, recursive: bool = True) -> list[FileRecord]:
        if not root.exists():
            return []
        iterator = root.rglob("*") if recursive else root.iterdir()
        records: list[FileRecord] = []
        for path in iterator:
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
                    dry_run_only=True,
                    reasons=[
                        f"classified as {record.category}",
                        "sha256=" + record.sha256[:12],
                    ],
                )
            )
        return proposals

    def apply_routes(
        self,
        proposals: list[FileRouteProposal],
        destination_root: Path,
    ) -> list[Path]:
        """Move files into categorized buckets under destination_root."""
        moved: list[Path] = []
        for proposal in proposals:
            source = Path(proposal.source_path)
            if not source.exists():
                continue
            target_dir = destination_root / proposal.target_bucket
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / proposal.suggested_name
            if target.exists():
                stem = target.stem
                suffix = target.suffix
                index = 1
                while target.exists():
                    target = target_dir / f"{stem}_{index}{suffix}"
                    index += 1
            shutil.move(str(source), str(target))
            proposal.dry_run_only = False
            proposal.reasons.append(f"moved to {target}")
            moved.append(target)
        return moved

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
        if suffix in {".pdf", ".doc", ".docx", ".txt", ".md"}:
            return "documents"
        if suffix in {".zip", ".7z", ".rar", ".tar", ".gz"}:
            return "archives"
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
            return "images"
        if suffix in {".py", ".ts", ".tsx", ".js", ".rs", ".go", ".java"}:
            return "code"
        if suffix in {".mp4", ".mkv", ".mov", ".avi"}:
            return "video"
        if suffix in {".mp3", ".wav", ".flac"}:
            return "audio"
        return "inbox"

    def _suggest_name(self, record: FileRecord) -> str:
        stem = Path(record.path).stem.replace(" ", "_").lower()
        return f"{record.category}_{stem}{record.suffix}"
