from __future__ import annotations

import ast
from pathlib import Path

from packages.perception import CodeGraphSummary


class CodeIntelligence:
    def index_python_tree(self, root: Path) -> CodeGraphSummary:
        files = sorted(root.rglob("*.py"))
        edges: dict[str, list[str]] = {}
        for file_path in files:
            module_imports = self._extract_imports(file_path)
            edges[str(file_path)] = module_imports
        return CodeGraphSummary(
            root=str(root),
            python_files=[str(file_path) for file_path in files],
            import_edges=edges,
        )

    def _extract_imports(self, path: Path) -> list[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        return imports
