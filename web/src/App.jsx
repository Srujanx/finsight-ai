import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { useMemoStream } from "./useMemoStream";
import "./App.css";

const EXAMPLE_TICKERS = ["NVDA", "AAPL", "JPM", "TSLA"];

export default function App() {
  const [ticker, setTicker] = useState("");
  const { steps, memo, error, running, run } = useMemoStream();

  const handleRun = (t) => {
    const value = (t || ticker).trim().toUpperCase();
    if (value) {
      setTicker(value);
      run(value);
    }
  };

  return (
    <div className="app">
      <div className="grid-bg" aria-hidden />

      <header className="hero">
        <div className="eyebrow">AUTONOMOUS EQUITY RESEARCH</div>
        <h1 className="title">
          FinSight<span className="title-accent">.AI</span>
        </h1>
        <p className="subtitle">
          An AI analyst that reads filings, news, and market data — then writes a
          memo where every claim cites its source.
        </p>

        <div className="search">
          <span className="search-prompt">$</span>
          <input
            className="search-input"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleRun()}
            placeholder="enter ticker"
            spellCheck={false}
            disabled={running}
          />
          <button className="search-btn" onClick={() => handleRun()} disabled={running || !ticker}>
            {running ? "ANALYZING" : "ANALYZE"}
          </button>
        </div>

        <div className="examples">
          <span className="examples-label">try</span>
          {EXAMPLE_TICKERS.map((t) => (
            <button key={t} className="chip" onClick={() => handleRun(t)} disabled={running}>
              {t}
            </button>
          ))}
        </div>
      </header>

      <AnimatePresence>
        {steps.length > 0 && (
          <motion.section
            className="pipeline"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <div className="pipeline-rail" />
            {steps.map((s, i) => {
              const isLast = i === steps.length - 1;
              const active = running && isLast;
              return (
                <motion.div
                  key={i}
                  className="step"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <span className={`step-dot ${active ? "step-dot--active" : "step-dot--done"}`} />
                  <span className="step-label">{s.label}</span>
                </motion.div>
              );
            })}
          </motion.section>
        )}
      </AnimatePresence>

      {error && (
        <motion.div className="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          Couldn't finish that one — {error}. Try another ticker.
        </motion.div>
      )}

      <AnimatePresence>
        {memo && (
          <motion.section
            className="memo"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="memo-tag">RESEARCH MEMO</div>
            <div className="memo-body">
              <ReactMarkdown>{memo}</ReactMarkdown>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      <footer className="footer">
        Educational tool · not investment advice · built with LangGraph + Gemini
      </footer>
    </div>
  );
}
