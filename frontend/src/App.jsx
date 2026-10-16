import {
  Activity,
  BrainCircuit,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  Network,
  Settings,
  ShieldCheck,
  UploadCloud,
  Code2,
  LoaderCircle,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  analyzeProject,
  getHealth,
  getImpact,
  getAIExplanation,
  getFunctionImpact,
} from "./api";
import DependencyGraph from "./DependencyGraph";

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Dependencies", icon: Network },
  { label: "Change Impact", icon: GitPullRequest },
  { label: "Function Analysis", icon: Code2 },
  { label: "AI Insights", icon: BrainCircuit },
];

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [selectedFile, setSelectedFile] = useState(null);
  const [projectData, setProjectData] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [activePage, setActivePage] = useState("Overview");
  const [selectedImpactPath, setSelectedImpactPath] = useState("");
  const [impactReport, setImpactReport] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactError, setImpactError] = useState("");
  const [aiReport, setAiReport] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [selectedFunction, setSelectedFunction] = useState(null);
  const [functionImpact, setFunctionImpact] = useState(null);
  const [functionLoading, setFunctionLoading] = useState(false);
  const [functionError, setFunctionError] = useState("");

  async function checkBackend() {
    setBackendStatus("checking");
    try {
      const data = await getHealth();
      setBackendStatus(
        data.falkordb === "connected" ? "connected" : "disconnected"
      );
    } catch {
      setBackendStatus("disconnected");
    }
  }

  useEffect(() => {
    checkBackend();
  }, []);

  async function handleAnalyze(event) {
    event.preventDefault();
    if (!selectedFile) {
      setError("Choose a ZIP file containing your Python project first.");
      return;
    }

    setUploading(true);
    setError("");
    try {
      const data = await analyzeProject(selectedFile);
      setProjectData(data);
      setSelectedImpactPath(data.files?.[0] || "");
      setImpactReport(null);
      setAiReport("");
      setFunctionImpact(null);
      setSelectedFunction(data.functions?.[0] || null);
      setActivePage("Overview");
    } catch (err) {
      setError(err.message || "Project analysis failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyzeImpact(event) {
    event.preventDefault();
    if (!selectedImpactPath) {
      setImpactError("Analyze a repository and select a file first.");
      return;
    }
    setImpactLoading(true);
    setImpactError("");
    setImpactReport(null);
    setAiReport("");
    setAiError("");
    try {
      setImpactReport(await getImpact(selectedImpactPath));
    } catch (err) {
      setImpactError(err.message || "Could not calculate file impact.");
    } finally {
      setImpactLoading(false);
    }
  }

  async function handleAIExplanation() {
    if (!selectedImpactPath) {
      setAiError("Select a file first.");
      return;
    }
    setAiLoading(true);
    setAiError("");
    setAiReport("");
    try {
      const result = await getAIExplanation(selectedImpactPath);
      setAiReport(result.report || "Gemini returned no explanation.");
    } catch (err) {
      setAiError(err.message || "Gemini explanation failed.");
    } finally {
      setAiLoading(false);
    }
  }

  async function handleFunctionImpact(event) {
    event.preventDefault();
    if (!selectedFunction) {
      setFunctionError("No function is selected.");
      return;
    }
    setFunctionLoading(true);
    setFunctionError("");
    setFunctionImpact(null);
    try {
      const result = await getFunctionImpact(selectedFunction.name, selectedFunction.file);
      setFunctionImpact(result.callers || []);
    } catch (err) {
      setFunctionError(err.message || "Could not load function impact.");
    } finally {
      setFunctionLoading(false);
    }
  }

  const metrics = [
    {
      label: "Files analyzed",
      value: projectData ? projectData.file_count : "—",
      icon: Code2,
    },
    {
      label: "Functions found",
      value: projectData ? projectData.function_count : "—",
      icon: Activity,
    },
    {
      label: "Dependencies",
      value: projectData ? projectData.dependency_count : "—",
      icon: Network,
    },
    {
      label: "Impact reports",
      value: projectData ? "Ready" : "—",
      icon: GitPullRequest,
    },
  ];

  return (
    <div className="min-h-screen bg-[#080d18] text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-800 bg-[#0b1120] p-5 md:block">
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-xl bg-indigo-500/15 p-2 text-indigo-300">
            <GitBranch size={24} />
          </div>
          <div>
            <h1 className="text-lg font-bold">RepoSage AI</h1>
            <p className="text-xs text-slate-500">Code intelligence</p>
          </div>
        </div>

        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
          Workspace
        </p>

        <nav className="space-y-1">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              onClick={() => setActivePage(label)}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${
                activePage === label
                  ? "bg-indigo-500/15 text-indigo-300"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>

        <div className="absolute bottom-5 left-5 right-5 rounded-xl border border-slate-800 p-3">
          <div className="flex items-center gap-2 text-sm">
            <ShieldCheck
              size={17}
              className={
                backendStatus === "connected"
                  ? "text-emerald-400"
                  : "text-slate-500"
              }
            />
            <span>Local workspace</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {backendStatus === "connected"
              ? "API and FalkorDB connected"
              : backendStatus === "checking"
                ? "Checking backend connection..."
                : "Backend connection unavailable"}
          </p>
        </div>
      </aside>

      <main className="md:ml-64">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 px-6 py-5 lg:px-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300">
              Developer workspace
            </p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight">
              {activePage}
            </h2>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-slate-800 px-3 py-2 text-xs text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === "connected"
                  ? "bg-emerald-400"
                  : backendStatus === "disconnected"
                    ? "bg-red-400"
                    : "bg-amber-400"
              }`}
            />
            {backendStatus === "connected"
              ? "FalkorDB connected"
              : backendStatus === "disconnected"
                ? "Backend unavailable"
                : "Connecting to backend..."}
            <button
              onClick={checkBackend}
              className="ml-1 rounded p-1 hover:bg-slate-800"
              title="Check connection again"
              aria-label="Check connection again"
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </header>

        <div className="space-y-7 p-6 lg:p-10">
          {activePage === "Overview" && (
            <>
              <section className="rounded-2xl border border-slate-800 bg-gradient-to-br from-[#121d35] to-[#0c1322] p-7 lg:p-9">
                <div className="max-w-2xl">
                  <span className="rounded-full border border-indigo-400/20 bg-indigo-400/10 px-3 py-1 text-xs text-indigo-300">
                    AI-assisted code analysis
                  </span>
                  <h3 className="mt-5 text-3xl font-bold leading-tight lg:text-4xl">
                    Understand the impact
                    <br />
                    before you change the code.
                  </h3>
                  <p className="mt-4 max-w-xl text-sm leading-6 text-slate-400">
                    Explore dependencies, discover potentially affected files,
                    and review AI-generated explanations for your Python project.
                  </p>

                  <form onSubmit={handleAnalyze} className="mt-6 space-y-3">
                    <label className="block text-sm font-medium text-slate-300">
                      Python project ZIP
                    </label>
                    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-700 bg-[#090f1c]/70 p-3">
                      <input
                        type="file"
                        accept=".zip,application/zip"
                        onChange={(event) => {
                          setSelectedFile(event.target.files?.[0] || null);
                          setError("");
                        }}
                        className="block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-800 file:px-4 file:py-2 file:font-medium file:text-white hover:file:bg-slate-700 sm:w-auto"
                      />
                      <span className="text-xs text-slate-500">
                        ZIP only · maximum 50 MB
                      </span>
                    </div>
                    <button
                      type="submit"
                      disabled={uploading || backendStatus !== "connected"}
                      className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {uploading ? (
                        <LoaderCircle size={18} className="animate-spin" />
                      ) : (
                        <UploadCloud size={18} />
                      )}
                      {uploading ? "Analyzing repository..." : "Analyze repository"}
                    </button>
                  </form>

                  {error && (
                    <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                      <AlertCircle size={18} className="mt-0.5 shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  {projectData && (
                    <div className="mt-4 flex items-center gap-2 text-sm text-emerald-300">
                      <CheckCircle2 size={17} />
                      Analyzed {projectData.project_name} successfully.
                    </div>
                  )}
                </div>
              </section>

              <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {metrics.map(({ label, value, icon: Icon }) => (
                  <div
                    key={label}
                    className="rounded-2xl border border-slate-800 bg-[#0d1525] p-5"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-400">{label}</p>
                      <Icon size={18} className="text-indigo-300" />
                    </div>
                    <p className="mt-5 text-3xl font-semibold">{value}</p>
                    <p className="mt-2 text-xs text-slate-500">
                      {projectData ? "From current repository analysis" : "Waiting for repository data"}
                    </p>
                  </div>
                ))}
              </section>

              {projectData && (
                <section className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <h3 className="font-semibold">Analyzed files</h3>
                    <span className="text-xs text-slate-500">
                      {projectData.files.length} files
                    </span>
                  </div>
                  <div className="space-y-2">
                    {projectData.files.map((file) => (
                      <div
                        key={file}
                        className="flex items-center gap-3 rounded-lg bg-[#080d18] px-3 py-2 text-sm"
                      >
                        <Code2 size={16} className="text-indigo-300" />
                        <span className="break-all text-slate-300">{file}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}

          {activePage === "Dependencies" && (
            <section className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
              <div className="flex items-center gap-2">
                <Network size={19} className="text-indigo-300" />
                <h3 className="font-semibold">Dependency explorer</h3>
              </div>
              <p className="mt-2 text-sm text-slate-400">
                {projectData
                  ? `${projectData.dependency_count} internal import relationships detected.`
                  : "Analyze a ZIP project from Overview to load dependency data."}
              </p>
              <div className="mt-5">
                <DependencyGraph />
              </div>
              {projectData?.dependencies?.length > 0 && (
                <div className="mt-5 space-y-2">
                  <h4 className="text-sm font-medium text-slate-300">Detected imports</h4>
                  {projectData.dependencies.map((edge, index) => (
                    <div
                      key={`${edge.source}-${edge.target}-${index}`}
                      className="rounded-lg border border-slate-800 p-3 text-sm"
                    >
                      <span className="text-slate-200">{edge.source}</span>
                      <span className="mx-2 text-indigo-300">→ imports →</span>
                      <span className="text-slate-200">{edge.target}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {activePage === "Change Impact" && (
            <section className="space-y-5">
              <div className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
                <div className="flex items-center gap-2">
                  <GitPullRequest size={19} className="text-indigo-300" />
                  <h3 className="font-semibold">Change Impact Intelligence</h3>
                </div>
                <p className="mt-2 text-sm text-slate-400">
                  Select a file to find upstream files that depend on it.
                </p>
                {!projectData ? (
                  <p className="mt-5 rounded-xl border border-slate-800 p-4 text-sm text-slate-400">
                    Analyze a Python ZIP from Overview before running impact analysis.
                  </p>
                ) : (
                  <form onSubmit={handleAnalyzeImpact} className="mt-5 space-y-4">
                    <label className="block text-sm font-medium text-slate-300" htmlFor="impact-file">
                      File you plan to change
                    </label>
                    <select
                      id="impact-file"
                      value={selectedImpactPath}
                      onChange={(event) => {
                        setSelectedImpactPath(event.target.value);
                        setImpactReport(null);
                        setAiReport("");
                        setImpactError("");
                        setAiError("");
                      }}
                      className="w-full rounded-xl border border-slate-700 bg-[#080d18] px-4 py-3 text-sm text-slate-200"
                    >
                      {projectData.files.map((file) => <option key={file} value={file}>{file}</option>)}
                    </select>
                    <button type="submit" disabled={impactLoading} className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-50">
                      {impactLoading && <LoaderCircle size={17} className="animate-spin" />}
                      {impactLoading ? "Analyzing impact..." : "Analyze change impact"}
                    </button>
                  </form>
                )}
                {impactError && <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{impactError}</p>}
              </div>

              {impactReport && (
                <>
                  <div className="grid gap-4 sm:grid-cols-3">
                    {[
                      { label: "Affected files", value: impactReport.affected_count ?? impactReport.affected_files?.length ?? 0 },
                      { label: "Maximum dependency depth", value: impactReport.maximum_depth ?? 0 },
                      { label: "Estimated severity", value: impactReport.severity || "UNKNOWN" },
                    ].map((item) => (
                      <div key={item.label} className="rounded-2xl border border-slate-800 bg-[#0d1525] p-5">
                        <p className="text-sm text-slate-400">{item.label}</p>
                        <p className="mt-3 break-words text-2xl font-semibold">{item.value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
                    <h3 className="font-semibold">Impact Advisor</h3>
                    <p className="mt-3 rounded-xl bg-[#080d18] p-4 text-sm leading-6 text-slate-300">{impactReport.summary || "Impact analysis completed."}</p>
                    <h4 className="mt-5 text-sm font-semibold">Potentially affected files</h4>
                    {impactReport.affected_files?.length ? (
                      <div className="mt-3 space-y-2">
                        {impactReport.affected_files.map((file, index) => (
                          <div key={`${file.path}-${index}`} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 p-3 text-sm">
                            <span className="break-all">{file.path}</span>
                            <span className="rounded-full bg-indigo-500/10 px-3 py-1 text-xs text-indigo-300">Depth {file.depth}</span>
                          </div>
                        ))}
                      </div>
                    ) : <p className="mt-3 text-sm text-slate-400">No dependent files were found in the static import graph. This does not guarantee the change is safe.</p>}
                    <h4 className="mt-5 text-sm font-semibold">Recommended actions</h4>
                    <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-300">
                      {(impactReport.recommendations || []).map((item, index) => <li key={index}>{item}</li>)}
                    </ul>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">Gemini AI Explanation</h3>
                        <p className="mt-1 text-sm text-slate-400">AI explanation grounded in dependency graph evidence.</p>
                      </div>
                      <button onClick={handleAIExplanation} disabled={aiLoading} className="inline-flex items-center gap-2 rounded-xl bg-violet-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-400 disabled:opacity-50">
                        {aiLoading && <LoaderCircle size={17} className="animate-spin" />}
                        {aiLoading ? "Generating..." : "Generate AI explanation"}
                      </button>
                    </div>
                    {aiError && <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{aiError}</p>}
                    {aiReport && <div className="mt-5 whitespace-pre-wrap rounded-xl border border-slate-800 bg-[#080d18] p-5 text-sm leading-7 text-slate-300">{aiReport}</div>}
                  </div>
                </>
              )}
            </section>
          )}

          {activePage === "Function Analysis" && (
            <section className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
              <div className="flex items-center gap-2">
                <Code2 size={19} className="text-indigo-300" />
                <h3 className="font-semibold">Function-Level Impact Analysis</h3>
              </div>
              <p className="mt-2 text-sm text-slate-400">Find functions that call the selected function, using CALLS relationships in FalkorDB.</p>
              {!projectData ? (
                <p className="mt-5 rounded-xl border border-slate-800 p-4 text-sm text-slate-400">Analyze a Python ZIP from Overview first.</p>
              ) : projectData.functions.length === 0 ? (
                <p className="mt-5 text-sm text-slate-400">No functions were discovered.</p>
              ) : (
                <form onSubmit={handleFunctionImpact} className="mt-5 space-y-4">
                  <label htmlFor="function-select" className="block text-sm font-medium text-slate-300">Function to inspect</label>
                  <select
                    id="function-select"
                    value={selectedFunction ? `${selectedFunction.file}::${selectedFunction.name}` : ""}
                    onChange={(event) => {
                      const fn = projectData.functions.find(item => `${item.file}::${item.name}` === event.target.value);
                      setSelectedFunction(fn || null);
                      setFunctionImpact(null);
                      setFunctionError("");
                    }}
                    className="w-full rounded-xl border border-slate-700 bg-[#080d18] px-4 py-3 text-sm text-slate-200"
                  >
                    {projectData.functions.map((fn, index) => <option key={`${fn.file}-${fn.name}-${index}`} value={`${fn.file}::${fn.name}`}>{fn.name}() — {fn.file}</option>)}
                  </select>
                  <button type="submit" disabled={functionLoading} className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-50">
                    {functionLoading && <LoaderCircle size={17} className="animate-spin" />}
                    {functionLoading ? "Checking callers..." : "Analyze function impact"}
                  </button>
                  {functionError && <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{functionError}</p>}
                  {functionImpact && (
                    <div className="space-y-3 pt-2">
                      <h4 className="text-sm font-semibold">Upstream callers</h4>
                      {functionImpact.length ? functionImpact.map((caller, index) => (
                        <div key={`${caller.file}-${caller.name}-${index}`} className="rounded-lg border border-slate-800 p-3">
                          <p className="text-sm font-medium">{caller.name}()</p>
                          <p className="mt-1 break-all text-xs text-slate-400">{caller.file}</p>
                          <p className="mt-2 text-xs text-indigo-300">Call depth: {caller.depth}</p>
                        </div>
                      )) : <p className="text-sm text-slate-400">No upstream callers were found in the CALLS graph.</p>}
                    </div>
                  )}
                </form>
              )}
            </section>
          )}

          {activePage === "AI Insights" && (
            <section className="rounded-2xl border border-slate-800 bg-[#0d1525] p-6">
              <div className="flex items-center gap-2">
                <BrainCircuit size={19} className="text-violet-300" />
                <h3 className="font-semibold">AI Impact Insights</h3>
              </div>
              <p className="mt-2 text-sm text-slate-400">Generate a Gemini explanation from Change Impact after selecting a file and running impact analysis.</p>
              {!projectData && <p className="mt-5 rounded-xl border border-slate-800 p-4 text-sm text-slate-400">Analyze a Python ZIP from Overview first.</p>}
              {projectData && !aiReport && (
              <button
                 onClick={async () => {
               const path = projectData.files?.[0];

      if (!path) {
        setAiError("No analyzed files found. Analyze a repository first.");
        return;
      }

      setAiError("");
      setAiReport("");

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/api/ai/explanation?path=${encodeURIComponent(path)}`,
          { method: "POST" }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Failed to generate AI explanation.");
        }

        setAiReport(data.report);
      } catch (error) {
        setAiError(error.message || "Could not connect to the backend.");
      }
    }}
    className="mt-5 rounded-xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-400"
  >
    Generate AI Explanation
  </button>
)}
              {aiReport && <div className="mt-5 whitespace-pre-wrap rounded-xl border border-slate-800 bg-[#080d18] p-5 text-sm leading-7 text-slate-300">{aiReport}</div>}
              {aiError && <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{aiError}</p>}
            </section>
          )}

          <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-5 text-xs text-slate-500">
            <span>RepoSage AI · Code Change Impact Analyzer</span>
            <span className="flex items-center gap-2">
              <Settings size={14} />
              Local development
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
