"use client";

import { useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/analyze";

export default function HomePage() {
  const [code, setCode] = useState("print('hello')");
  const [helpMode, setHelpMode] = useState("guided");
  const [hintDepth, setHintDepth] = useState(1);
  const [includeComplexity, setIncludeComplexity] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [showSolution, setShowSolution] = useState(false);

  const requestPayload = useMemo(
    () => ({
      code,
      help_mode: helpMode,
      hint_depth: hintDepth,
      include_complexity: includeComplexity,
      include_solution: helpMode === "guided",
    }),
    [code, helpMode, hintDepth, includeComplexity]
  );

  async function analyzeCode() {
    setLoading(true);
    setError("");
    setResult(null);
    setShowSolution(false);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestPayload),
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(payload.detail || "Analysis failed.");
        return;
      }
      setResult(payload);
    } catch {
      setError("Could not reach the backend. Start it first on http://localhost:8000.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-shell">
      <header>
        <h1>Python Tutor (AI-Assisted)</h1>
        <p>
          Paste code, get beginner-friendly feedback, guided hints, and optional improved code.
        </p>
      </header>

      <section className="card">
        <label htmlFor="code">Python code</label>
        <textarea
          id="code"
          rows={16}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Paste your Python code here"
        />

        <div className="controls">
          <label className="inline-checkbox">
            <input
              type="checkbox"
              checked={includeComplexity}
              onChange={(e) => setIncludeComplexity(e.target.checked)}
            />
            Explain complexity
          </label>

          <label>
            Help mode
            <select
              value={helpMode}
              onChange={(e) => setHelpMode(e.target.value)}
            >
              <option value="guided">Guided help</option>
              <option value="diagnostic">Quick diagnostic only</option>
            </select>
          </label>

          {helpMode === "guided" ? (
            <label>
              Hint depth
              <select
                value={hintDepth}
                onChange={(e) => setHintDepth(Number(e.target.value))}
              >
                <option value={1}>1 - Hint only</option>
                <option value={2}>2 - Step clues</option>
                <option value={3}>3 - Near-solution approach</option>
              </select>
            </label>
          ) : null}
        </div>

        <button onClick={analyzeCode} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze code"}
        </button>
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      {result ? (
        <section className="card results">
          <h2>What happened</h2>
          <p>{result.summary}</p>

          <h2>Focus areas</h2>
          <ul>
            {result.error_clusters?.length ? (
              result.error_clusters.map((item) => (
                <li key={`${item.type}-${item.line}-${item.why}`}>
                  <strong>{item.type === "Potential issue" ? "Potential improvement" : item.type}</strong>
                  (line {item.line || "n/a"})
                  <p>{item.why}</p>
                  {item.snippet ? <code>{item.snippet}</code> : null}
                </li>
              ))
            ) : (
              <li>No static issues were detected.</li>
            )}
          </ul>

          {helpMode === "guided" ? (
            <>
              <h2>Hints</h2>
              <ul>
                {result.hints?.length ? (
                  result.hints.map((hint) => (
                    <li key={`${hint.level}-${hint.text.slice(0, 20)}`}>
                      <strong>{hint.level}</strong>: {hint.text}
                    </li>
                  ))
                ) : (
                  <li>No hints were needed for this run.</li>
                )}
              </ul>
            </>
          ) : null}

          {result.key_concepts?.length ? (
            <>
              <h2>Key concepts</h2>
              <ul>
                {result.key_concepts?.map((concept) => (
                  <li key={concept}>{concept}</li>
                ))}
              </ul>
            </>
          ) : null}

          {result.complexity ? (
            <>
              <h2>Complexity</h2>
              <p>Time: {result.complexity.time}</p>
              <p>Space: {result.complexity.space}</p>
            </>
          ) : null}

          {result.best_practices?.length ? (
            <>
              <h2>Best practices</h2>
              <ul>
                {result.best_practices?.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : null}

          {helpMode === "guided" ? (
            <button
              className="secondary"
              onClick={() => setShowSolution((prev) => !prev)}
              disabled={!result.full_solution}
            >
              {showSolution ? "Hide corrected code" : "Show corrected code"}
            </button>
          ) : null}

          {showSolution && result.full_solution ? (
            <div className="solution-block">
              <p>{result.full_solution.explanation}</p>
              {result.full_solution.code ? (
                <pre>{result.full_solution.code}</pre>
              ) : (
                <p>No corrected version available yet.</p>
              )}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
