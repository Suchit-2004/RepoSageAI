
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from falkordb import FalkorDB

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from main import analyze_project
from impact_advisor import (
    generate_impact_report,
    generate_ai_impact_report,
)

GRAPH_NAME = "reposage"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024
MAX_FILES = 5000

app = FastAPI(title="RepoSage AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_graph():
    db = FalkorDB(host="localhost", port=6379)
    return db.select_graph(GRAPH_NAME)


def extract_zip_safely(contents: bytes, destination: Path) -> Path:
    """Extract a ZIP without allowing path traversal."""
    try:
        archive = zipfile.ZipFile(__import__("io").BytesIO(contents))
    except zipfile.BadZipFile as exc:
        raise ValueError("The uploaded file is not a valid ZIP.") from exc

    with archive:
        entries = archive.infolist()

        if len(entries) > MAX_FILES:
            raise ValueError("The ZIP contains too many entries.")

        total_size = sum(entry.file_size for entry in entries)
        if total_size > MAX_EXTRACTED_BYTES:
            raise ValueError("The expanded ZIP exceeds 200 MB.")

        root = destination.resolve()
        python_files = 0

        for entry in entries:
            if entry.is_dir():
                continue

            name = entry.filename.replace("\\", "/")
            relative = PurePosixPath(name)

            if (
                relative.is_absolute()
                or not relative.parts
                or any(part in ("", ".", "..") for part in relative.parts)
                or ":" in relative.parts[0]
            ):
                raise ValueError("Unsafe path detected in ZIP.")

            # Reject Unix symbolic links.
            unix_mode = (entry.external_attr >> 16) & 0xFFFF
            if unix_mode & 0o170000 == 0o120000:
                raise ValueError("Symbolic links are not supported.")

            target = (root / Path(*relative.parts)).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Unsafe path detected in ZIP.")

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)

            if target.suffix.lower() == ".py":
                python_files += 1

        if python_files == 0:
            raise ValueError("No Python files were found in the ZIP.")

    # If the ZIP contains one enclosing project folder, analyze that folder.
    children = list(destination.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]

    return destination


@app.get("/api/health")
def health():
    try:
        graph = get_graph()
        graph.ro_query("RETURN 1")
        return {"api": "ok", "falkordb": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"FalkorDB connection failed: {exc}",
        ) from exc


@app.post("/api/projects/analyze")
async def analyze_uploaded_project(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Upload a ZIP file containing Python source files.",
        )

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="ZIP uploads must be 50 MB or smaller.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="reposage_") as temp:
            project_dir = extract_zip_safely(
                contents,
                Path(temp) / "project",
            )
            analyze_project(project_dir, graph_name=GRAPH_NAME)

        graph = get_graph()
        files = graph.ro_query(
            "MATCH (f:File) RETURN f.path ORDER BY f.path"
        ).result_set
        functions = graph.ro_query(
            "MATCH (f:File)-[:DEFINES]->(fn:Function) "
            "RETURN fn.name, f.path ORDER BY f.path, fn.name"
        ).result_set
        edges = graph.ro_query(
            "MATCH (a:File)-[:IMPORTS]->(b:File) "
            "RETURN a.path, b.path ORDER BY a.path, b.path"
        ).result_set

        return {
            "project_name": file.filename,
            "files": [row[0] for row in files],
            "functions": [
                {"name": row[0], "file": row[1]}
                for row in functions
            ],
            "dependencies": [
                {"source": row[0], "target": row[1]}
                for row in edges
            ],
            "file_count": len(files),
            "function_count": len(functions),
            "dependency_count": len(edges),
        }

    except (ValueError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Project analysis failed: {exc}",
        ) from exc


@app.get("/api/dependencies")
def dependencies():
    graph = get_graph()
    files = graph.ro_query(
        "MATCH (f:File) RETURN f.path ORDER BY f.path"
    ).result_set
    edges = graph.ro_query(
        "MATCH (a:File)-[:IMPORTS]->(b:File) "
        "RETURN a.path, b.path ORDER BY a.path, b.path"
    ).result_set

    return {
        "nodes": [{"id": row[0], "label": row[0].split("/")[-1]} for row in files],
        "edges": [
            {"source": row[0], "target": row[1], "label": "imports"}
            for row in edges
        ],
    }


@app.get("/api/impact")
def file_impact(path: str):
    graph = get_graph()
    exists = graph.ro_query(
        "MATCH (f:File {path: $path}) RETURN f.path",
        {"path": path},
    ).result_set

    if not exists:
        raise HTTPException(status_code=404, detail="File not found.")

    affected = graph.ro_query(
        """
        MATCH (dependent:File)-[:IMPORTS*1..10]->(changed:File {path: $path})
        RETURN dependent.path, min(length(
            shortestPath((dependent)-[:IMPORTS*1..10]->(changed))
        )) AS depth
        ORDER BY depth, dependent.path
        """,
        {"path": path},
    ).result_set

    depths = {row[0]: int(row[1]) for row in affected}
    return generate_impact_report(path, depths)


@app.get("/api/functions")
def functions():
    graph = get_graph()
    result = graph.ro_query(
        """
        MATCH (f:File)-[:DEFINES]->(fn:Function)
        RETURN fn.name, f.path
        ORDER BY f.path, fn.name
        """
    )
    return {
        "functions": [
            {"name": row[0], "file": row[1]}
            for row in result.result_set
        ]
    }


@app.get("/api/function-impact")
def function_impact(name: str, file: str):
    graph = get_graph()
    result = graph.ro_query(
        """
        MATCH path = (caller:Function)-[:CALLS*1..10]->(
            target:Function {name: $name, file: $file}
        )
        RETURN caller.name, caller.file, length(path)
        ORDER BY length(path), caller.file, caller.name
        """,
        {"name": name, "file": file},
    )
    return {
        "callers": [
            {"name": row[0], "file": row[1], "depth": int(row[2])}
            for row in result.result_set
        ]
    }


@app.post("/api/ai/explanation")
def ai_explanation(path: str):
    graph = get_graph()
    exists = graph.ro_query(
        "MATCH (f:File {path: $path}) RETURN f.path",
        {"path": path},
    ).result_set

    if not exists:
        raise HTTPException(status_code=404, detail="File not found.")

    affected = graph.ro_query(
        """
        MATCH (dependent:File)-[:IMPORTS*1..10]->(changed:File {path: $path})
        RETURN dependent.path, min(length(
            shortestPath((dependent)-[:IMPORTS*1..10]->(changed))
        )) AS depth
        ORDER BY depth, dependent.path
        """,
        {"path": path},
    ).result_set

    depths = {row[0]: int(row[1]) for row in affected}
    report = generate_impact_report(path, depths)

    edge_result = graph.ro_query(
        """
        MATCH (source:File)-[:IMPORTS]->(target:File)
        RETURN source.path, target.path
        ORDER BY source.path, target.path
        """
    )

    edges = [
        {"source": row[0], "target": row[1]}
        for row in edge_result.result_set
    ]

    try:
        text = generate_ai_impact_report(report, edges)
        return {"report": text}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini explanation failed: {exc}",
        ) from exc
