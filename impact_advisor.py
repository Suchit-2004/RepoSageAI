
import os

from google import genai


def generate_impact_report(changed_file, affected_depths):
    """Create a deterministic report from dependency graph evidence."""
    affected_count = len(affected_depths)
    max_depth = max(affected_depths.values(), default=0)

    if affected_count == 0:
        severity = "LOW"
        summary = (
            f"No dependent files were found for {changed_file}. "
            "This does not guarantee that the change is safe."
        )
    elif affected_count >= 5 or max_depth >= 4:
        severity = "HIGH"
        summary = (
            f"Changing {changed_file} may affect "
            f"{affected_count} files across multiple dependency levels."
        )
    elif affected_count >= 2 or max_depth >= 2:
        severity = "MEDIUM"
        summary = (
            f"Changing {changed_file} may affect "
            f"{affected_count} dependent files."
        )
    else:
        severity = "LOW"
        summary = (
            f"Changing {changed_file} has a limited "
            "dependency impact in the current graph."
        )

    affected = [
        {
            "path": path,
            "depth": depth,
            "relationship": (
                "Direct dependency"
                if depth == 1
                else f"Indirect dependency ({depth} levels)"
            ),
        }
        for path, depth in sorted(
            affected_depths.items(),
            key=lambda item: (item[1], item[0]),
        )
    ]

    recommendations = [
        "Review the changed file and its callers.",
        "Run tests covering the changed file and affected files.",
        "Check function signatures, return values, and exceptions.",
    ]

    if affected_count >= 2 or max_depth >= 2:
        recommendations.append(
            "Run integration tests across the dependency chain."
        )

    return {
        "changed_file": changed_file,
        "severity": severity,
        "summary": summary,
        "affected_count": affected_count,
        "maximum_depth": max_depth,
        "affected_files": affected,
        "recommendations": recommendations,
        "analysis_type": "Rule-based dependency analysis",
    }


def generate_ai_impact_report(rule_report, dependency_edges):
    """Ask Gemini to explain graph evidence without inventing code facts."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Set it in the "
            "PowerShell terminal and restart Streamlit."
        )

    client = genai.Client(api_key=api_key)

    evidence = {
        "changed_file": rule_report["changed_file"],
        "rule_based_severity": rule_report["severity"],
        "affected_files": rule_report["affected_files"],
        "direct_import_edges": dependency_edges,
    }

    prompt = f"""
You are RepoSage AI, a cautious code change impact analyst.

Analyze the following dependency-graph evidence:
{evidence}

Return a concise Markdown report with these headings:
1. Impact explanation
2. Main dependency paths
3. Potential risks
4. Recommended tests
5. Limitations

Rules:
- Treat the supplied graph as evidence of static import relationships only.
- Do not claim to have inspected source code, function bodies, test coverage,
  or runtime behavior; that evidence was not provided.
- Do not invent dependencies or code defects.
- Distinguish confirmed graph relationships from possible risks.
- If no affected files are listed, explain that static graph analysis
  found none; do not conclude that the change is safe.
- Treat the rule-based severity as a heuristic, not a probability.
- Keep the report specific and concise.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text
