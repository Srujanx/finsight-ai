import { useState, useCallback } from "react";

// Connects to the SSE endpoint and surfaces progress + final memo.
export function useMemoStream() {
  const [steps, setSteps] = useState([]);      // progress events as they arrive
  const [memo, setMemo] = useState(null);       // final memo markdown
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

  const run = useCallback((ticker) => {
    setSteps([]);
    setMemo(null);
    setError(null);
    setRunning(true);

    // In dev, Vite proxies /api to localhost:8000 (see vite.config). In prod,
    // same origin, so a relative URL works in both.
    const source = new EventSource(`/api/memo/${ticker}`);

    source.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === "progress") {
        setSteps((prev) => [...prev, event]);
      } else if (event.type === "done") {
        setMemo(event.memo_markdown);
        setRunning(false);
        source.close();
      } else if (event.type === "error") {
        setError(event.message);
        setRunning(false);
        source.close();
      }
    };

    source.onerror = () => {
      setError("Connection lost");
      setRunning(false);
      source.close();
    };
  }, []);

  return { steps, memo, error, running, run };
}
