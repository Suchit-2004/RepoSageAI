import argparse
import ast
from pathlib import Path

from falkordb import FalkorDB

ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT = ROOT / "sample_project"
GRAPH_NAME = "reposage"


class CodeAnalyzer(ast.NodeVisitor):
    """Extract function definitions, imports, and function calls."""

    def __init__(self):
        self.functions = []
        self.imports = set()
        self.calls = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        previous = self.current_function
        self.current_function = node.name
        for child in node.body:
            self.visit(child)
        self.current_function = previous

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split(".")[0])

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module.split(".")[0])

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called_name = node.func.attr
        else:
            called_name = None

        if called_name:
            self.calls.append((self.current_function, called_name))

        self.generic_visit(node)


def analyze_file(path):
    """Return function names, imported modules, and function calls."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        print(f"Skipping {path}: {exc}")
        return [], [], []

    analyzer = CodeAnalyzer()
    analyzer.visit(tree)
    return (
        sorted(set(analyzer.functions)),
        sorted(analyzer.imports),
        analyzer.calls,
    )


def analyze_project(project_dir, graph_name=GRAPH_NAME):
    """Build file, function, import, and call relationships."""
    project_dir = Path(project_dir).resolve()
    if not project_dir.is_dir():
        raise FileNotFoundError(f"Project folder not found: {project_dir}")

    files = sorted(project_dir.rglob("*.py"))
    if not files:
        raise ValueError(f"No Python files found in {project_dir}")

    db = FalkorDB(host="localhost", port=6379)
    graph = db.select_graph(graph_name)

    # Rebuild the selected graph for this project.
    graph.query("MATCH (n) DETACH DELETE n")

    # Store project-relative paths, never temporary extraction directory names.
    def graph_path(path):
        return path.relative_to(project_dir).as_posix()

    module_to_path = {}
    for path in files:
        # If duplicate module stems exist, don't guess which one an import means.
        module_to_path.setdefault(path.stem, [])
        module_to_path[path.stem].append(graph_path(path))

    file_info = {}
    function_info = []

    for path in files:
        relative_path = graph_path(path)
        functions, imports, calls = analyze_file(path)
        file_info[relative_path] = imports

        graph.query(
            "MERGE (f:File {path: $path})",
            {"path": relative_path},
        )

        for function in functions:
            graph.query(
                """
                MERGE (fn:Function {name: $name, file: $file})
                WITH fn
                MATCH (f:File {path: $file})
                MERGE (f)-[:DEFINES]->(fn)
                """,
                {"name": function, "file": relative_path},
            )

        for caller, callee in calls:
            if caller:
                function_info.append((relative_path, caller, callee))

    # Create file-level import relationships only when a module maps uniquely.
    for source, imports in file_info.items():
        for module in imports:
            candidates = module_to_path.get(module, [])
            if len(candidates) != 1:
                continue
            target = candidates[0]
            if target == source:
                continue

            graph.query(
                """
                MATCH (a:File {path: $source})
                MATCH (b:File {path: $target})
                MERGE (a)-[:IMPORTS]->(b)
                """,
                {"source": source, "target": target},
            )

    # Resolve function calls only when caller and callee names are unambiguous.
    definitions = graph.ro_query(
        """
        MATCH (f:File)-[:DEFINES]->(fn:Function)
        RETURN f.path, fn.name
        """
    )

    definitions_by_name = {}
    for row in definitions.result_set:
        definitions_by_name.setdefault(row[1], []).append((row[0], row[1]))

    for source_path, caller_name, callee_name in function_info:
        callers = [
            item for item in definitions_by_name.get(caller_name, [])
            if item[0] == source_path
        ]
        callees = definitions_by_name.get(callee_name, [])

        if len(callers) != 1 or len(callees) != 1:
            continue

        caller_file, caller = callers[0]
        callee_file, callee = callees[0]

        graph.query(
            """
            MATCH (caller:Function {name: $caller, file: $caller_file})
            MATCH (callee:Function {name: $callee, file: $callee_file})
            MERGE (caller)-[:CALLS]->(callee)
            """,
            {
                "caller": caller,
                "caller_file": caller_file,
                "callee": callee,
                "callee_file": callee_file,
            },
        )

    print(f"\nAnalyzed {len(files)} Python files.")
    print(f"Graph: {graph_name}")

    print("\nFile dependencies:")
    dependencies = graph.ro_query(
        """
        MATCH (a:File)-[:IMPORTS]->(b:File)
        RETURN a.path, b.path
        ORDER BY a.path, b.path
        """
    )
    for row in dependencies.result_set:
        print(f"{row[0]} imports {row[1]}")

    print("\nFunction calls:")
    calls_result = graph.ro_query(
        """
        MATCH (a:Function)-[:CALLS]->(b:Function)
        RETURN a.name, a.file, b.name, b.file
        ORDER BY a.file, a.name, b.name
        """
    )
    if calls_result.result_set:
        for row in calls_result.result_set:
            print(f"{row[1]}::{row[0]} calls {row[3]}::{row[2]}")
    else:
        print("No uniquely resolved function calls found. Some calls may be ambiguous or external.")

    return graph


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Python dependencies with RepoSage AI."
    )
    parser.add_argument(
        "--project",
        default=str(DEFAULT_PROJECT),
        help="Path to the Python project folder to analyze.",
    )
    args = parser.parse_args()
    analyze_project(args.project)


if __name__ == "__main__":
    main()
