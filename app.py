
import shutil

import streamlit as st
from falkordb import FalkorDB
from streamlit_agraph import agraph, Node, Edge, Config
from impact_advisor import (
    generate_impact_report,
    generate_ai_impact_report,
)
from project_uploader import extract_python_project
from main import analyze_project


st.set_page_config(
    page_title="RepoSage AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --rs-bg: #0b1020; --rs-panel: #121a2b; --rs-border: #26344c;
              --rs-muted: #9aabc4; --rs-accent: #7c9cff; }
      .stApp { background: var(--rs-bg); }
      [data-testid="stHeader"] { background: rgba(11, 16, 32, 0.92); }
      [data-testid="stSidebar"] { background: #0e1627; border-right: 1px solid var(--rs-border); }
      [data-testid="stSidebar"] * { color: #e7edf8; }
      .block-container { max-width: 1440px; padding-top: 1.7rem; padding-bottom: 3rem; }
      h1, h2, h3 { letter-spacing: -0.025em; }
      h1 { font-size: 2.25rem !important; font-weight: 750 !important; }
      h2, h3 { font-weight: 680 !important; }
      [data-testid="stMetric"] {
        background: var(--rs-panel); border: 1px solid var(--rs-border);
        padding: 1rem 1.1rem; border-radius: 14px;
      }
      [data-testid="stMetricLabel"] { color: var(--rs-muted); }
      [data-testid="stMetricValue"] { color: #f4f7ff; }
      div[data-testid="stFileUploader"] {
        background: var(--rs-panel); border: 1px dashed #405473;
        border-radius: 14px; padding: .7rem;
      }
      div.stButton > button {
        border-radius: 9px; border: 1px solid #405780; font-weight: 650;
        padding: .55rem 1rem; transition: all .15s ease;
      }
      div.stButton > button[kind="primary"] {
        background: #6f8fff; border-color: #6f8fff; color: #081020;
      }
      div.stButton > button:hover { border-color: #9cb2ff; transform: translateY(-1px); }
      div[data-testid="stAlert"] { border-radius: 10px; }
      hr { border-color: var(--rs-border); }
      code { border-radius: 5px; }
      .rs-eyebrow { color: #9fb4ff; font-size: .76rem; font-weight: 750;
                    letter-spacing: .13em; text-transform: uppercase; }
      .rs-subtitle { color: var(--rs-muted); font-size: 1rem; margin-top: -.55rem; }
      .rs-panel { background: var(--rs-panel); border: 1px solid var(--rs-border);
                  padding: 1rem 1.15rem; border-radius: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="rs-eyebrow">CODE INTELLIGENCE WORKSPACE</div>', unsafe_allow_html=True)
st.title("RepoSage AI")
st.markdown(
    '<div class="rs-subtitle">Understand code dependencies. Estimate change impact. Review AI-assisted recommendations.</div>',
    unsafe_allow_html=True,
)
st.divider()


# --------------------------------------------------
# Repository Upload
# --------------------------------------------------
st.subheader("01  /  Analyze repository")
st.write("Upload a ZIP containing Python source files. RepoSage builds a dependency graph for the project.")

uploaded_zip = st.file_uploader(
    "Choose a Python project ZIP",
    type=["zip"],
    key="project_zip",
)

if st.button(
    "Analyze uploaded project",
    type="primary",
    disabled=uploaded_zip is None,
):
    extracted_dir = None

    try:
        with st.spinner("Extracting and analyzing project..."):
            extracted_dir = extract_python_project(uploaded_zip)
            analyze_project(extracted_dir)

            st.session_state["reposage_project_name"] = uploaded_zip.name
            st.session_state.pop("impact_report", None)
            st.session_state.pop("ai_impact_report", None)

        st.success("Project analyzed successfully!")
        st.rerun()

    except Exception as exc:
        st.error(f"Project analysis failed: {exc}")

    finally:
        if extracted_dir is not None:
            shutil.rmtree(extracted_dir, ignore_errors=True)


# --------------------------------------------------
# Dashboard and Graph
# --------------------------------------------------
try:
    db = FalkorDB(host="localhost", port=6379)
    graph = db.select_graph("reposage")

    files_result = graph.ro_query(
        """
        MATCH (f:File)
        RETURN f.path
        ORDER BY f.path
        """
    )
    files = [row[0] for row in files_result.result_set]

    if not files:
        st.warning(
            "No files found. Upload a project or run `python main.py`."
        )
        st.stop()

    functions_result = graph.ro_query(
        "MATCH (fn:Function) RETURN count(fn)"
    )
    function_count = functions_result.result_set[0][0]

    col1, col2 = st.columns(2)
    col1.metric("Files analyzed", len(files))
    col2.metric("Functions discovered", function_count)

    st.success("Connected to FalkorDB")

    st.markdown("### Workspace")
    tab_dependencies, tab_functions, tab_impact = st.tabs(
        ["Dependencies", "Function Analysis", "Change Impact"]
    )

    with tab_dependencies:
        # --------------------------------------------------
        # Dependency Explorer
        # --------------------------------------------------
        st.subheader("Dependency Explorer")

        selected_file = st.selectbox(
            "Select a file",
            files,
            key="dependency_file",
        )

        dependencies = graph.ro_query(
            """
            MATCH (source:File {path: $path})
                  -[:IMPORTS*1..5]->(dependency:File)
            RETURN DISTINCT dependency.path
            ORDER BY dependency.path
            """,
            {"path": selected_file},
        )

        dependency_paths = [
            row[0] for row in dependencies.result_set
        ]

        if dependency_paths:
            st.write("**This file depends on:**")
            for path in dependency_paths:
                st.markdown(f"- `{path}`")
        else:
            st.info("No dependencies found for this file.")

        # --------------------------------------------------
        # Interactive Dependency Graph
        # --------------------------------------------------
        st.subheader("Interactive Dependency Graph")

        edges_result = graph.ro_query(
            """
            MATCH (source:File)-[:IMPORTS]->(target:File)
            RETURN source.path, target.path
            ORDER BY source.path, target.path
            """
        )

        nodes = [
            Node(
                id=path,
                label=path.rsplit("/", 1)[-1],
                size=34,
                title=path,
                color="#527DFF",
                font={"color": "#E6EEFF", "size": 18},
            )
            for path in files
        ]

        edges = [
            Edge(
                source=row[0],
                target=row[1],
                label="imports",
                color="#8094B8",
                font={"color": "#D8E2F5", "size": 13},
            )
            for row in edges_result.result_set
        ]

        config = Config(
            width="100%",
            height=650,
            directed=True,
            physics=True,
            hierarchical=True,
            nodeHighlightBehavior=True,
            highlightColor="#7C9CFF",
            collapsible=False,
            node={
                    "labelProperty": "label",
                    "fontSize": 18,
                    "fontColor": "#E6EEFF",
                    "color": "#527DFF",
                    "borderWidth": 2,
                    "borderWidthSelected": 4,
    },
    link={
        "labelProperty": "label",
        "renderLabel": True,
        "color": "#8094B8",
        "fontColor": "#D8E2F5",
        "fontSize": 13,
    },
)

        if edges:
            agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.info(
                "No internal file imports were detected. "
                "Try a project with multiple Python modules importing one another."
            )
            agraph(nodes=nodes, edges=[], config=config)

    with tab_functions:
        # --------------------------------------------------
        # Function Call Explorer
        # --------------------------------------------------
        st.subheader("Function Call Explorer")
        st.caption(
            "Explore function-to-function calls discovered in the source code."
        )

        calls_result = graph.ro_query(
            """
            MATCH (caller:Function)-[:CALLS]->(callee:Function)
            RETURN caller.name, caller.file, callee.name, callee.file
            ORDER BY caller.file, caller.name, callee.file, callee.name
            """
        )

        function_calls = calls_result.result_set

        if function_calls:
            function_options = sorted({
                f"{row[1]}::{row[0]}"
                for row in function_calls
            })

            selected_function = st.selectbox(
                "Select a function to inspect",
                function_options,
                key="selected_function",
            )

            matching_calls = [
                row for row in function_calls
                if f"{row[1]}::{row[0]}" == selected_function
            ]

            st.markdown("#### Calls made by this function")

            for row in matching_calls:
                caller_name, caller_file, callee_name, callee_file = row

                st.markdown(
                    f"- `{caller_file}::{caller_name}` calls "
                    f"`{callee_file}::{callee_name}`"
                )

            with st.expander("View all discovered function calls"):
                for row in function_calls:
                    caller_name, caller_file, callee_name, callee_file = row
                    st.markdown(
                        f"- `{caller_file}::{caller_name}` → "
                        f"`{callee_file}::{callee_name}`"
                    )
        else:
            st.info(
                "No uniquely resolved function calls found. "
                "Analyze a project using the updated analyzer."
            )


        # --------------------------------------------------
        # Function-Level Impact Analysis
        # --------------------------------------------------
        st.subheader("Function-Level Impact Analysis")
        st.caption(
            "Find functions that may be affected when a function changes."
        )

        function_result = graph.ro_query(
            """
            MATCH (f:Function)
            RETURN f.name, f.file
            ORDER BY f.file, f.name
            """
        )

        function_rows = function_result.result_set

        if function_rows:
            # Use tuples internally to avoid ambiguity when names repeat.
            function_lookup = {
                f"{row[1]}::{row[0]}": (row[1], row[0])
                for row in function_rows
            }

            selected_target = st.selectbox(
                "Select a function you plan to change",
                list(function_lookup.keys()),
                key="function_impact_target",
            )

            if st.button("Analyze function impact"):
                target_file, target_name = function_lookup[selected_target]

                function_impact_result = graph.ro_query(
                    """
                    MATCH path =
                        (caller:Function)-[:CALLS*1..10]->
                        (target:Function {
                            name: $name,
                            file: $file
                        })
                    RETURN caller.name, caller.file, length(path) AS depth
                    ORDER BY depth, caller.file, caller.name
                    """,
                    {
                        "name": target_name,
                        "file": target_file,
                    },
                )

                impacted = {}

                for row in function_impact_result.result_set:
                    caller_name, caller_file, depth = row
                    key = (caller_file, caller_name)

                    if key not in impacted or depth < impacted[key]:
                        impacted[key] = depth

                if impacted:
                    st.warning(
                        f"{len(impacted)} potentially affected function(s)"
                    )

                    for (caller_file, caller_name), depth in sorted(
                        impacted.items(),
                        key=lambda item: (
                            item[1],
                            item[0][0],
                            item[0][1],
                        ),
                    ):
                        relationship = (
                            "Direct caller"
                            if depth == 1
                            else f"Indirect caller · {depth} levels"
                        )

                        st.markdown(
                            f"- `{caller_file}::{caller_name}` — "
                            f"{relationship}"
                        )
                else:
                    st.info(
                        "No callers were found in the current function-call graph. "
                        "This does not guarantee that the function has no callers."
                    )
        else:
            st.info(
                "No function nodes found. Analyze a project to populate "
                "function-level relationships."
            )

    with tab_impact:
        # --------------------------------------------------
        # File-Level Change Impact Intelligence
        # --------------------------------------------------
        st.subheader("Change Impact Intelligence")
        st.caption(
            "Estimate which files may be affected before changing a file."
        )

        changed_file = st.selectbox(
            "Which file are you considering changing?",
            files,
            key="changed_file",
        )

        if st.button("Analyze change impact", type="primary"):
            impact_result = graph.ro_query(
                """
                MATCH path =
                    (affected:File)-[:IMPORTS*1..5]->
                    (changed:File {path: $path})
                RETURN affected.path, length(path) AS depth
                ORDER BY depth, affected.path
                """,
                {"path": changed_file},
            )

            affected_depths = {}

            for row in impact_result.result_set:
                path, depth = row[0], row[1]

                if path != changed_file:
                    if (
                        path not in affected_depths
                        or depth < affected_depths[path]
                    ):
                        affected_depths[path] = depth

            report = generate_impact_report(
                changed_file=changed_file,
                affected_depths=affected_depths,
            )

            st.session_state["impact_report"] = report
            st.session_state.pop("ai_impact_report", None)

        report = st.session_state.get("impact_report")

        if report:
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric(
                "Affected files",
                report["affected_count"],
            )
            metric_col2.metric(
                "Maximum dependency depth",
                report["maximum_depth"],
            )
            metric_col3.metric(
                "Estimated impact",
                report["severity"],
            )

            st.markdown("### Impact Advisor")
            st.info(report["summary"])
            st.caption(f"Analysis type: {report['analysis_type']}")

            if report["affected_files"]:
                st.markdown("#### Potentially affected files")

                for item in report["affected_files"]:
                    st.markdown(
                        f"- `{item['path']}` — {item['relationship']}"
                    )
            else:
                st.warning(
                    "No dependent files were found. "
                    "This does not guarantee that the change is safe."
                )

            st.markdown("#### Recommended actions")
            for recommendation in report["recommendations"]:
                st.markdown(f"- {recommendation}")

            # --------------------------------------------------
            # Gemini AI Impact Explanation
            # --------------------------------------------------
            st.markdown("### Gemini AI Impact Explanation")
            st.caption(
                "Generate an explanation from the dependency graph. "
                "Gemini does not inspect source code in this step."
            )

            if st.button("Generate AI explanation", key="gemini_impact"):
                try:
                    dependency_edges = [
                        {"source": row[0], "target": row[1]}
                        for row in edges_result.result_set
                    ]

                    with st.spinner("Gemini is analyzing graph evidence..."):
                        ai_report = generate_ai_impact_report(
                            rule_report=report,
                            dependency_edges=dependency_edges,
                        )

                    st.session_state["ai_impact_report"] = ai_report

                except Exception as exc:
                    st.error(f"AI explanation failed: {exc}")

            ai_report = st.session_state.get("ai_impact_report")
            if ai_report:
                st.markdown(ai_report)
                st.caption(
                    "AI-generated explanation based on dependency graph evidence. "
                    "Verify recommendations before acting."
                )

except Exception as exc:
    st.error(f"Something went wrong: {exc}")
    st.info(
        "Check that Docker is running and the reposage-db container "
        "is active. If the graph is empty, analyze a project first."
    )
