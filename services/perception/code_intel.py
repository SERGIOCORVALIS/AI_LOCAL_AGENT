from __future__ import annotations

import ast
import os
from pathlib import Path

from packages.perception import CodeGraphSummary


class CodeIntelligence:
    """AST-based Python code intelligence for imports, symbols, and call edges."""

    _SKIP_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
    }

    def index_python_tree(self, root: Path) -> CodeGraphSummary:
        files = self._iter_python_files(root)
        import_edges: dict[str, list[str]] = {}
        symbols: dict[str, list[str]] = {}
        call_edges: dict[str, list[str]] = {}
        for file_path in files:
            key = str(file_path)
            import_edges[key] = self._extract_imports(file_path)
            symbols[key] = self._extract_symbols(file_path)
            call_edges[key] = self._extract_calls(file_path)
        return CodeGraphSummary(
            root=str(root),
            python_files=[str(file_path) for file_path in files],
            import_edges=import_edges,
            symbols=symbols,
            call_edges=call_edges,
        )

    def _iter_python_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for current_root, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name for name in dirnames if name not in self._SKIP_DIRS
            ]
            for filename in filenames:
                if filename.endswith(".py"):
                    files.append(Path(current_root) / filename)
        return sorted(files)

    def _parse(self, path: Path) -> ast.AST | None:
        try:
            return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            return None

    def _extract_imports(self, path: Path) -> list[str]:
        tree = self._parse(path)
        if tree is None:
            return []
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        return sorted(set(imports))

    def _extract_symbols(self, path: Path) -> list[str]:
        tree = self._parse(path)
        if not isinstance(tree, ast.Module):
            return []
        symbols: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                symbols.append(f"function:{node.name}")
            elif isinstance(node, ast.ClassDef):
                symbols.append(f"class:{node.name}")
                for child in node.body:
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                        symbols.append(f"method:{node.name}.{child.name}")
        return symbols

    def _extract_calls(self, path: Path) -> list[str]:
        tree = self._parse(path)
        if tree is None:
            return []
        calls: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = self._call_name(node.func)
            if name:
                calls.append(name)
        return sorted(set(calls))

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._call_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return None
