
import ast
from pathlib import Path


def analyze_file(file_path: str) -> dict:
    """Extract basic code relationships from a Python file."""
    path = Path(file_path)

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return {
            "file": path.name,
            "functions": [],
            "imports": [],
            "calls": [],
            "error": str(exc),
        }

    functions = []
    imports = []
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

    return {
        "file": path.name,
        "functions": sorted(set(functions)),
        "imports": sorted(set(imports)),
        "calls": sorted(set(calls)),
        "error": None,
    }


if __name__ == "__main__":
    result = analyze_file("test_graph.py")
    print(result)
