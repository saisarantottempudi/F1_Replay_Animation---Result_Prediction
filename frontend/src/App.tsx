import { useEffect, useState } from "react";
import { getJSON } from "./api/client";

type Health = { status: string };

export default function App() {
  const [health, setHealth] = useState<string>("Checking backend...");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const data = await getJSON<Health>("/health");
        setHealth(`Backend says: ${data.status}`);
      } catch (e: any) {
        setError(e.message || "Unknown error");
        setHealth("Backend not reachable");
      }
    })();
  }, []);

  return (
    <div style={{ padding: 20, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto" }}>
      <h1 style={{ marginTop: 0 }}>F1 Replay + Prediction</h1>

      <div style={{ padding: 14, border: "1px solid #333", borderRadius: 12, maxWidth: 520 }}>
        <div><b>Status:</b> {health}</div>
        {error ? (
          <div style={{ marginTop: 8 }}>
            <b>Error:</b> {error}<br />
            <span style={{ opacity: 0.8 }}>
              Make sure backend is running on <code>http://127.0.0.1:8000</code>
            </span>
          </div>
        ) : null}
      </div>

      <p style={{ marginTop: 16, opacity: 0.8 }}>
        Next: dropdowns (Season/Race/Session) + Replay canvas + Weather & Track Evolution timeline.
      </p>
    </div>
  );
}
