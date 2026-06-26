import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useMemoStream } from "./useMemoStream";

export default function App() {
  const [ticker, setTicker] = useState("");
  const { steps, memo, error, running, run } = useMemoStream();

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", fontFamily: "system-ui", padding: 16 }}>
      <h1>FinSight AI</h1>
      <p>Enter a ticker to generate a cited investment memo.</p>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="e.g. NVDA"
          style={{ flex: 1, padding: 8 }}
        />
        <button onClick={() => run(ticker)} disabled={running || !ticker}>
          {running ? "Analyzing…" : "Analyze"}
        </button>
      </div>

      {steps.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Progress</h3>
          <ul>
            {steps.map((s, i) => (
              <li key={i}>{s.label}</li>
            ))}
          </ul>
        </div>
      )}

      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {memo && (
        <div style={{ marginTop: 24 }}>
          <h3>Memo</h3>
          <ReactMarkdown>{memo}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
