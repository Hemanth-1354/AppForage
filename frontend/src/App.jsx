import { useState, useRef, useEffect } from "react";
import "./index.css";

const API = "https://appforage.onrender.com";

// ── UTILITY ─────────────────────────────────────────────────────────────────

function cx(...args) {
  return args.filter(Boolean).join(" ");
}

// ── ICONS ────────────────────────────────────────────────────────────────────

const IconBolt = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);
const IconCheck = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const IconX = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);
const IconChevron = ({ open }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
    style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
    <polyline points="9 18 15 12 9 6" />
  </svg>
);
const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
  </svg>
);
const IconPlay = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polygon points="5 3 19 12 5 21 5 3" />
  </svg>
);

// ── EXAMPLE PROMPTS ──────────────────────────────────────────────────────────

const EXAMPLES = [
  "Build a CRM with login, contacts, dashboard, role-based access (admin, sales rep, viewer), and premium plan with Stripe payments. Admins can see analytics.",
  "Build a project management tool like Jira. Users create projects, tasks with status, assign to team members. Free plan: 3 projects. Pro: unlimited + time tracking.",
  "Build an LMS where instructors create video courses and quizzes. Students enroll, track progress, get certificates. Premium users get live sessions.",
  "Build a support ticket system with SLA tracking, agent assignment, canned responses, and customer satisfaction ratings."
];

// ── PIPELINE STAGE DISPLAY ───────────────────────────────────────────────────

function StageCard({ name, data, latency, index }) {
  const [open, setOpen] = useState(false);

  const stageColors = ["#00ff9d", "#00d4ff", "#ff6b35", "#a855f7", "#fbbf24"];
  const color = stageColors[index % stageColors.length];

  return (
    <div className="stage-card" style={{ "--accent": color }}>
      <button className="stage-header" onClick={() => setOpen(!open)}>
        <span className="stage-num" style={{ color }}>0{index + 1}</span>
        <span className="stage-name">{name}</span>
        {latency && <span className="stage-latency">{latency}ms</span>}
        <IconChevron open={open} />
      </button>
      {open && (
        <div className="stage-body">
          <JsonViewer data={data} />
        </div>
      )}
    </div>
  );
}

// ── JSON VIEWER ──────────────────────────────────────────────────────────────

function JsonViewer({ data }) {
  const [copied, setCopied] = useState(false);
  const str = JSON.stringify(data, null, 2);

  const copy = () => {
    navigator.clipboard.writeText(str);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="json-viewer">
      <button className="copy-btn" onClick={copy}>
        <IconCopy /> {copied ? "Copied!" : "Copy"}
      </button>
      <pre className="json-pre">{str}</pre>
    </div>
  );
}

// ── METRICS BAR ──────────────────────────────────────────────────────────────

function MetricsBar({ metrics, quality }) {
  const costStr = metrics?.total_cost ? `$${metrics.total_cost.toFixed(5)}` : "$0.00";
  const items = [
    { label: "Total Latency", value: `${metrics?.total_latency_ms || 0}ms` },
    { label: "Est. Cost", value: costStr },
    { label: "Retries", value: metrics?.retries || 0 },
    { label: "Quality Score", value: `${quality || 0}/100` },
  ];

  return (
    <div className="metrics-bar">
      {items.map(item => (
        <div key={item.label} className="metric-item">
          <span className="metric-value">{item.value}</span>
          <span className="metric-label">{item.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── VALIDATION PANEL ─────────────────────────────────────────────────────────

function ValidationPanel({ validation }) {
  if (!validation) return null;
  const errors = validation.errors || [];
  const warnings = validation.warnings || [];
  const score = validation.score || 0;

  return (
    <div className="validation-panel">
      <div className="val-header">
        <div className={cx("val-badge", validation.valid ? "val-pass" : "val-fail")}>
          {validation.valid ? <IconCheck /> : <IconX />}
          {validation.valid ? "VALID" : "INVALID"}
        </div>
        <div className="quality-ring">
          <span className="quality-num">{score}</span>
          <span className="quality-label">Quality</span>
        </div>
      </div>
      {errors.length > 0 && (
        <div className="val-section">
          <div className="val-section-title error-title">Errors ({errors.length})</div>
          {errors.map((e, i) => (
            <div key={i} className="val-item val-error">
              <span className="val-layer">[{e.layer}]</span> {e.message}
            </div>
          ))}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="val-section">
          <div className="val-section-title warn-title">Warnings ({warnings.length})</div>
          {warnings.map((w, i) => (
            <div key={i} className="val-item val-warn">
              <span className="val-layer">[{w.layer}]</span> {w.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── CODE ARTIFACTS TAB ───────────────────────────────────────────────────────

function CodeArtifacts({ result }) {
  const [activeTab, setActiveTab] = useState("schema.sql");
  const artifacts = result?.runtime?.code_artifacts || {};
  const tabs = Object.keys(artifacts);
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(artifacts[activeTab] || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (tabs.length === 0) return null;

  return (
    <div className="artifacts-panel">
      <div className="artifacts-title">Generated Code Artifacts</div>
      <div className="tabs">
        {tabs.map(tab => (
          <button key={tab} className={cx("tab", activeTab === tab && "tab-active")} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>
      <div className="artifact-body">
        <button className="copy-btn" onClick={copy}>
          <IconCopy /> {copied ? "Copied!" : "Copy"}
        </button>
        <pre className="json-pre">{artifacts[activeTab]}</pre>
      </div>
    </div>
  );
}

// ── EVAL DASHBOARD ───────────────────────────────────────────────────────────

function EvalDashboard() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [subset, setSubset] = useState("real");

  const run = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subset })
      });
      setResults(await res.json());
    } catch (e) {
      alert("Evaluation failed: " + e.message);
    }
    setLoading(false);
  };

  return (
    <div className="eval-dashboard">
      <div className="eval-header">
        <h2 className="eval-title">Evaluation Framework</h2>
        <p className="eval-subtitle">10 real product prompts + 10 edge cases (vague, conflicting, incomplete)</p>
        <div className="eval-controls">
          <select className="eval-select" value={subset} onChange={e => setSubset(e.target.value)}>
            <option value="real">Real Prompts (10)</option>
            <option value="edge">Edge Cases (10)</option>
            <option value="all">Full Suite (20)</option>
          </select>
          <button className="run-eval-btn" onClick={run} disabled={loading}>
            {loading ? "Running..." : <><IconPlay /> Run Evaluation</>}
          </button>
        </div>
      </div>

      {loading && (
        <div className="eval-loading">
          <div className="loading-spinner" />
          <span>Running evaluation suite — this calls the full pipeline for each prompt...</span>
        </div>
      )}

      {results && !loading && (
        <div className="eval-results">
          <div className="eval-summary">
            <div className="summary-stat">
              <span className="stat-big green">{results.success_rate_pct}%</span>
              <span className="stat-label">Success Rate</span>
            </div>
            <div className="summary-stat">
              <span className="stat-big">{results.avg_latency_ms}ms</span>
              <span className="stat-label">Avg Latency</span>
            </div>
            <div className="summary-stat">
              <span className="stat-big">${(results.results || []).reduce((sum, r) => sum + (r.metrics?.total_cost || 0), 0).toFixed(4)}</span>
              <span className="stat-label">Total Est. Cost</span>
            </div>
            <div className="summary-stat">
              <span className="stat-big">{results.avg_quality_score}</span>
              <span className="stat-label">Avg Quality</span>
            </div>
            <div className="summary-stat">
              <span className="stat-big red">{results.failed}</span>
              <span className="stat-label">Failed</span>
            </div>
          </div>

          <div className="result-rows">
            {(results.results || []).map(r => (
              <div key={r.id} className={cx("result-row", r.success ? "row-pass" : "row-fail")}>
                <span className="result-id">{r.id}</span>
                <span className="result-name">{r.name}</span>
                <span className="result-status" style={{color: r.success ? 'var(--green)' : 'var(--red)'}}>
                  {r.success ? <IconCheck /> : <IconX />}
                </span>
                <span className="result-score">{r.quality_score || "—"}/100</span>
                <span className="result-latency">{r.latency_ms}ms</span>
                <span className="result-cost" style={{fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text3)'}}>${r.metrics?.total_cost ? r.metrics.total_cost.toFixed(5) : "0.00"}</span>
                {r.clarifications_needed && <span className="result-tag">needs clarification</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── MAIN APP ─────────────────────────────────────────────────────────────────

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [view, setView] = useState("compiler"); // "compiler" | "eval"
  const [phase, setPhase] = useState("");
  const textRef = useRef(null);

  const PHASES = [
    "Extracting intent...",
    "Designing architecture...",
    "Generating schemas...",
    "Refining consistency...",
    "Validating output...",
    "Finalizing..."
  ];

  const compile = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);

    // Phase indicator
    let phaseIdx = 0;
    const phaseInterval = setInterval(() => {
      setPhase(PHASES[phaseIdx % PHASES.length]);
      phaseIdx++;
    }, 3500);

    try {
      const res = await fetch(`${API}/api/compile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Compilation failed");
      }
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    }

    clearInterval(phaseInterval);
    setPhase("");
    setLoading(false);
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) compile();
  };

  const useExample = (ex) => {
    setPrompt(ex);
    textRef.current?.focus();
  };

  const stages = result ? [
    { name: "Intent Extraction", data: result.pipeline_stages?.intent, latency: result.metrics?.stages?.intent },
    { name: "Architecture Design", data: result.pipeline_stages?.architecture, latency: result.metrics?.stages?.architecture },
    { name: "Schema Generation", data: result.pipeline_stages?.raw_schema, latency: result.metrics?.stages?.schema_generation },
    { name: "Refinement", data: result.pipeline_stages?.refinement, latency: result.metrics?.stages?.refinement },
    { name: "Validation", data: result.pipeline_stages?.validation, latency: result.metrics?.stages?.validation },
    { name: "Runtime Simulation", data: result.runtime, latency: result.metrics?.stages?.runtime_simulation },
  ].filter(s => s.data) : [];

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon"><IconBolt /></span>
            <span className="logo-text">AppForge</span>
            <span className="logo-tag">NL → App Compiler</span>
          </div>
          <nav className="nav">
            <button className={cx("nav-btn", view === "compiler" && "nav-active")} onClick={() => setView("compiler")}>
              Compiler
            </button>
            <button className={cx("nav-btn", view === "eval" && "nav-active")} onClick={() => setView("eval")}>
              Evaluator
            </button>
          </nav>
        </div>
      </header>

      <main className="main">
        {view === "compiler" ? (
          <div className="compiler-view">
            {/* Input Section */}
            <div className="input-section">
              <div className="input-label">Describe your application</div>
              <div className="input-box">
                <textarea
                  ref={textRef}
                  className="prompt-input"
                  placeholder="Build a CRM with login, contacts, dashboard, role-based access (admin, sales rep, viewer), and premium plan with payments..."
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  onKeyDown={handleKey}
                  rows={5}
                />
                <div className="input-footer">
                  <span className="input-hint">⌘ + Enter to compile</span>
                  <button className="compile-btn" onClick={compile} disabled={loading || !prompt.trim()}>
                    {loading ? (
                      <><span className="spinner" /> {phase || "Compiling..."}</>
                    ) : (
                      <><IconBolt /> Compile App</>
                    )}
                  </button>
                </div>
              </div>
              <div className="examples">
                <span className="examples-label">Try an example:</span>
                {EXAMPLES.map((ex, i) => (
                  <button key={i} className="example-chip" onClick={() => useExample(ex)}>
                    {ex.slice(0, 50)}...
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="error-banner">
                <IconX /> {error}
              </div>
            )}

            {result && (
              <div className="results">
                {/* Status Banner */}
                <div className={cx("status-banner", result.success ? "status-success" : "status-partial")}>
                  <div className="status-icon">{result.success ? <IconCheck /> : "⚠"}</div>
                  <div>
                    <div className="status-title">{result.success ? "Compilation Successful" : "Compiled with Warnings"}</div>
                    {result.assumptions_made?.length > 0 && (
                      <div className="status-sub">Assumptions: {result.assumptions_made.join(" · ")}</div>
                    )}
                    {result.clarifications_needed?.length > 0 && (
                      <div className="status-sub warn-text">Ambiguities detected — reasonable defaults applied. Consider clarifying: {result.clarifications_needed.slice(0, 2).join(", ")}</div>
                    )}
                  </div>
                </div>

                {/* Metrics */}
                <MetricsBar metrics={result.metrics} quality={result.quality_score} />

                {/* Pipeline Stages */}
                <div className="section-title">Pipeline Stages</div>
                <div className="stages">
                  {stages.map((s, i) => (
                    <StageCard key={i} index={i} name={s.name} data={s.data} latency={s.latency} />
                  ))}
                </div>

                {/* Validation */}
                <div className="section-title">Validation Report</div>
                <ValidationPanel validation={result.validation} />

                {/* Final Schema */}
                <div className="section-title">Final Schema Output</div>
                <JsonViewer data={result.schema} />

                {/* Code Artifacts */}
                {result.runtime && <CodeArtifacts result={result} />}
              </div>
            )}
          </div>
        ) : (
          <EvalDashboard />
        )}
      </main>
    </div>
  );
}
