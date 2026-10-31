import { useMemo, useState } from "react";
import { apiUrl } from "./services/api.js";

const demoSources = [
  {
    name: "Sample portal notice (illustrative)",
    text: "The 2026 Future Scholars Award is open to undergraduate applicants with a household income below INR 500,000 per year. Applications close November 15, 2026. Applicants must upload a government income certificate only, academic transcripts, and proof of enrollment. The award provides INR 80,000 per year. Apply through the official scholarship portal.",
  },
  {
    name: "Sample guidance PDF (illustrative)",
    text: "For the 2026 Future Scholars Award, applicants must have a GPA of at least 3.2 and household income below INR 500,000. The last date to apply is December 10, 2026. Applicants must submit income tax returns only, academic transcripts, and a recommendation letter. The annual scholarship amount is INR 80,000. Applications are submitted through the scholarship portal.",
  },
];

const blankSource = () => ({ name: "", text: "", url: "" });

function App() {
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState([blankSource()]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("all");
  const [checked, setChecked] = useState({});
  const [urlDraft, setUrlDraft] = useState("");

  const visibleEvidence = useMemo(
    () =>
      (result?.evidence_matrix ?? []).filter((item) =>
        view === "all" ? true : view === "sourced" ? !item.is_inferred : item.is_inferred,
      ),
    [result, view],
  );

  function updateSource(index, field, value) {
    setSources((current) =>
      current.map((source, sourceIndex) =>
        sourceIndex === index ? { ...source, [field]: value } : source,
      ),
    );
  }

  function useDemo() {
    setQuery("What should I verify before applying for the Future Scholars Award?");
    setSources(demoSources.map((source) => ({ ...source, url: "" })));
    setResult(null);
    setChecked({});
    setError("");
  }

  async function addUrl() {
    const url = urlDraft.trim();
    if (!url) return;
    let name = url;
    try {
      name = new URL(url).hostname;
    } catch {
      setError("Enter a complete source URL beginning with https://");
      return;
    }
    setSources((current) => [...current.filter((source) => source.text || source.url), { name, url, text: "" }]);
    setUrlDraft("");
    setError("");
  }

  async function addFile(event, index) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(apiUrl("/api/extract"), { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not read the file.");
      setSources((current) => {
        const next = [...current];
        const source = next[index] ?? blankSource();
        next[index] = {
          ...source,
          name: source.name || data.name,
          text: [source.text, data.text].filter(Boolean).join("\n\n"),
          url: "",
        };
        return next;
      });
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function analyze(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    const payloadSources = sources
      .filter((source) => source.text.trim() || source.url.trim())
      .map((source, index) => ({
        name: source.name.trim() || `Source ${index + 1}`,
        ...(source.text.trim() ? { text: source.text.trim() } : {}),
        ...(source.url.trim() ? { url: source.url.trim() } : {}),
      }));
    if (payloadSources.length === 0) {
      setError("Add at least one source as text, a PDF/TXT upload, or a public web URL.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(apiUrl("/api/research"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), sources: payloadSources }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Analysis failed. Check your sources and try again.");
      setResult(data);
      setChecked({});
    } catch (requestError) {
      setError(requestError.message || "Could not connect to StarlightAI. Start the app with python run_starlight.py.");
    } finally {
      setBusy(false);
    }
  }

  const completedCount = (result?.verification_checklist ?? []).filter(
    (item) => checked[item.id],
  ).length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="StarlightAI home">
          <span className="brand-mark"><span /></span>
          <span>starlight<span className="brand-ai">ai</span></span>
        </a>
        <div className="topbar-right">
          <span className="engine-status"><i /> Research engine ready</span>
          <a className="github-link" href="https://github.com/" target="_blank" rel="noreferrer">About the project <span>↗</span></a>
        </div>
      </header>

      <main>
        <section className="pitch-banner">
          <div className="pitch-icon">✦</div>
          <div>
            <div className="pitch-kicker">JUDGE WALKTHROUGH <span>2 MIN</span></div>
            <p>Start with the scholarship preset. Spot missing renewal rules, compare conflicting deadlines, then build your verification checklist.</p>
          </div>
          <button className="button button-pitch" onClick={useDemo}>Load instant demo <span>→</span></button>
        </section>

        <section className="hero">
          <div className="eyebrow"><span className="eyebrow-line" /> INFORMATION GAP DETECTION</div>
          <h1>Find the gaps hiding<br />between the <span>sources.</span></h1>
          <p>Decisions deserve more than a summary. See what's supported, what's missing, and what doesn't agree.</p>
          <div className="hero-proof">
            <span><b>01</b> Compare sources</span><span className="proof-divider" />
            <span><b>02</b> Surface blind spots</span><span className="proof-divider" />
            <span><b>03</b> Know what to verify</span>
          </div>
        </section>

        <section className="workspace-grid">
          <form className="panel research-panel" onSubmit={analyze}>
            <div className="panel-heading">
              <div><span className="step-label">01 / RESEARCH BRIEF</span><h2>What do you need to know?</h2></div>
              <span className="panel-number">01</span>
            </div>
            <label className="field-label" htmlFor="query">YOUR QUESTION OR DECISION</label>
            <textarea
              id="query"
              className="query-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="e.g. What should I verify before applying for this scholarship?"
              required
              minLength={3}
              maxLength={500}
            />
            <div className="sources-heading">
              <label className="field-label">SOURCE MATERIAL <span>{sources.filter((source) => source.text.trim() || source.url.trim()).length} added</span></label>
              <span className="source-hint">Text, public URL, PDF or TXT</span>
            </div>
            <div className="source-list">
              {sources.map((source, index) => (
                <article className="source-card" key={`source-${index}`}>
                  <div className="source-card-top">
                    <span className="source-index">S{String(index + 1).padStart(2, "0")}</span>
                    <input
                      className="source-name"
                      aria-label={`Source ${index + 1} name`}
                      placeholder="Source name (e.g. Official notice)"
                      value={source.name}
                      onChange={(event) => updateSource(index, "name", event.target.value)}
                      maxLength={160}
                    />
                    {sources.length > 1 && <button className="icon-button remove-source" type="button" aria-label="Remove source" onClick={() => setSources((current) => current.filter((_, sourceIndex) => sourceIndex !== index))}>×</button>}
                  </div>
                  {source.url ? (
                    <div className="url-added"><span>↗</span> {source.url}</div>
                  ) : (
                    <textarea
                      className="source-text"
                      aria-label={`Source ${index + 1} text`}
                      placeholder="Paste source text here. Keep each claim traceable to its original source."
                      value={source.text}
                      onChange={(event) => updateSource(index, "text", event.target.value)}
                      maxLength={40000}
                    />
                  )}
                  {!source.url && (
                    <div className="source-card-foot">
                      <span>{source.text.length.toLocaleString()} / 40,000 chars</span>
                      <label className="upload-button">↑ Upload PDF / TXT<input type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" onChange={(event) => addFile(event, index)} /></label>
                    </div>
                  )}
                </article>
              ))}
            </div>
            <div className="source-actions">
              <button className="text-button" type="button" onClick={() => setSources((current) => [...current, blankSource()])}>＋ Add text source</button>
              <span className="action-separator" />
              <div className="url-entry"><input aria-label="Public source URL" type="url" placeholder="https:// source URL" value={urlDraft} onChange={(event) => setUrlDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addUrl(); } }} /><button type="button" aria-label="Add URL" onClick={addUrl}>Add URL</button></div>
            </div>
            {error && <div className="error-message" role="alert"><span>!</span>{error}</div>}
            <button className="button button-analyze" type="submit" disabled={busy}>
              {busy ? <><span className="spinner" /> Reading your sources…</> : <>Map the information gaps <span>→</span></>}
            </button>
            <p className="privacy-note"><span>◈</span> Sources are analyzed for this request and not saved.</p>
          </form>

          <aside className="panel methodology-panel">
            <span className="step-label">THE DARK SPOT METHOD</span>
            <h2>More than what's<br />written down.</h2>
            <p className="method-copy">The most important detail is often the one no source mentions.</p>
            <div className="method-steps">
              <div className="method-step"><span className="method-icon icon-evidence">✓</span><div><strong>Evidence, with receipts</strong><small>Every extracted statement links to a source quote.</small></div></div>
              <div className="method-step"><span className="method-icon icon-gap">◌</span><div><strong>Missing prerequisites</strong><small>See which decision-critical criteria are absent.</small></div></div>
              <div className="method-step"><span className="method-icon icon-conflict">⇄</span><div><strong>Conflicts in plain sight</strong><small>Compare mismatched claims side by side.</small></div></div>
              <div className="method-step"><span className="method-icon icon-verify">◎</span><div><strong>A next-step checklist</strong><small>Turn uncertainty into something actionable.</small></div></div>
            </div>
            <div className="method-footer"><span className="signal-dot" /> NO BLACK-BOX CERTAINTY <span>•</span> SOURCE-FIRST BY DESIGN</div>
          </aside>
        </section>

        {result && (
          <section className="results-section" aria-live="polite">
            <div className="results-title-row">
              <div><span className="step-label">02 / YOUR RESEARCH MAP</span><h2>Here's what the sources <span>don't tell you.</span></h2></div>
              <div className="score-card"><div className="score-ring"><strong>{result.overall_completeness_score}</strong><small>%</small></div><div><b>Source coverage</b><span>Not a truth score</span></div></div>
            </div>
            <div className="result-summary"><span className="summary-spark">✦</span><p>{result.summary}</p><span className="source-count">{result.sources_reviewed.length} SOURCES REVIEWED</span></div>

            <div className="radar-row">
              <div className="panel radar-panel">
                <div className="section-heading"><div><span className="step-label">GAP SEVERITY RADAR</span><h3>What still needs an answer</h3></div><span className="count-pill">{result.gaps.length} gaps</span></div>
                <div className="severity-grid">
                  {["critical", "high", "medium", "low"].map((level) => (
                    <div className={`severity-card severity-${level}`} key={level}><span>{level}</span><strong>{result.gap_severity_radar[level]}</strong><div className="severity-track"><i style={{ width: `${result.gap_severity_radar[level] ? Math.max(12, Math.min(100, result.gap_severity_radar[level] * 30)) : 0}%` }} /></div></div>
                  ))}
                </div>
                <div className="gap-list">
                  {result.gaps.length === 0 ? <div className="empty-state">Every tracked information area appears in the supplied text. Confirm each detail with its issuing source.</div> : result.gaps.map((gap) => (
                    <article className="gap-card" key={gap.id}>
                      <span className={`severity-tag tag-${gap.severity.toLowerCase()}`}>{gap.severity}</span>
                      <div><h4>{gap.title}</h4><p>{gap.description}</p><small>{gap.affected_area} <span>·</span> Heuristic signal, not proof of absence</small></div>
                    </article>
                  ))}
                </div>
              </div>
              <div className="panel conflict-panel">
                <div className="section-heading"><div><span className="step-label">CROSS-SOURCE CHECK</span><h3>Claims that don't align</h3></div><span className="conflict-count">{result.conflicts.length}</span></div>
                {result.conflicts.length === 0 ? <div className="empty-state conflict-empty">No direct conflict signals found. That doesn't guarantee the sources agree on everything.</div> : <div className="conflict-list">{result.conflicts.map((conflict) => (
                  <article className="conflict-card" key={conflict.id}>
                    <div className="conflict-topic"><span>⇄</span>{conflict.topic}</div>
                    <div className="quote-pair"><blockquote><small>SOURCE A · {conflict.source_a.name}</small>{conflict.source_a.claim}</blockquote><div className="versus">VS</div><blockquote><small>SOURCE B · {conflict.source_b.name}</small>{conflict.source_b.claim}</blockquote></div>
                    <p className="resolution-note"><b>Don't guess.</b> {conflict.resolution_advice}</p>
                  </article>
                ))}</div>}
                {result.freshness_warnings.length > 0 && <div className="freshness-block"><div className="freshness-title"><span>◷</span> DATE & FRESHNESS CHECK</div>{result.freshness_warnings.map((warning) => <div className="freshness-item" key={warning.source}><span>{warning.status}</span><p>{warning.warning}<small>{warning.source}{warning.detected_year ? ` · ${warning.detected_year}` : ""}</small></p></div>)}</div>}
              </div>
            </div>

            <div className="bottom-grid">
              <div className="panel evidence-panel">
                <div className="section-heading"><div><span className="step-label">EVIDENCE & UNCERTAINTY</span><h3>What we can actually support</h3></div></div>
                <div className="evidence-tabs" role="tablist" aria-label="Evidence filter">
                  {[["all", "All signals"], ["sourced", "● Sourced"], ["inferred", "✦ Inferred prompts"]].map(([key, label]) => <button key={key} type="button" role="tab" aria-selected={view === key} className={view === key ? "active" : ""} onClick={() => setView(key)}>{label}</button>)}
                </div>
                <div className="evidence-list">{visibleEvidence.length === 0 ? <div className="empty-state">Nothing in this view yet.</div> : visibleEvidence.map((item, index) => <article className={`evidence-item ${item.is_inferred ? "evidence-inferred" : ""}`} key={`${item.source}-${index}`}><span className={`evidence-badge ${item.is_inferred ? "badge-inferred" : "badge-sourced"}`}>{item.is_inferred ? "✦ INFERRED PROMPT" : "✓ SOURCE QUOTE"}</span><p>{item.claim}</p><small>{item.confidence}</small></article>)}</div>
                <p className="methodology-note">{result.analysis_note}</p>
              </div>
              <div className="panel checklist-panel">
                <div className="section-heading"><div><span className="step-label">03 / ACTION CENTER</span><h3>Before you decide</h3></div><span className="count-pill">{completedCount}/{result.verification_checklist.length}</span></div>
                <div className="checklist-progress"><span style={{ width: `${result.verification_checklist.length ? completedCount / result.verification_checklist.length * 100 : 0}%` }} /></div>
                <div className="checklist">{result.verification_checklist.length === 0 ? <div className="empty-state">No priority checks surfaced. Verify the key details directly before making a decision.</div> : result.verification_checklist.map((item) => <label className={`check-item ${checked[item.id] ? "is-checked" : ""}`} key={item.id}><input type="checkbox" checked={Boolean(checked[item.id])} onChange={() => setChecked((current) => ({ ...current, [item.id]: !current[item.id] }))} /><span className="custom-check">✓</span><span className="check-task"><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span>{item.task}</span></label>)}</div>
              </div>
            </div>
          </section>
        )}

        <footer className="footer"><a className="footer-brand" href="#">✦ STARLIGHTAI</a><span>Less guessing. Better questions.</span><span>Research responsibly · Verify with the source</span></footer>
      </main>
    </div>
  );
}

export default App;
