import { useEffect, useMemo, useState } from "react";
import { getTyreDegradation } from "../api/f1";
import type { TyreDegradationResponse } from "../api/f1";
import { normalizeCompound, tyreGradient } from "../theme/tyres";

type Props = {
  season: number;
  round: number;
  session: string; // ideally "R"
  drivers?: string[]; // e.g. ["VER","LEC",...]
};

export default function TyreDegradationPanel({ season, round, session, drivers = [] }: Props) {
  const [driver, setDriver] = useState<string>(drivers[0] ?? "");
  const [data, setData] = useState<TyreDegradationResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  // Keep selected driver valid when list changes
  useEffect(() => {
    if (!drivers.includes(driver)) {
      setDriver(drivers[0] ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drivers.join("|")]);

  useEffect(() => {
    if (session !== "R") return;
    if (!driver) return;
    setLoading(true);
    setError("");
    setData(null);

    getTyreDegradation(season, round, session, driver)
      .then(setData)
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, [season, round, session, driver]);

  const sortedStints = useMemo(() => {
    if (!data) return [];
    return [...data.stints].sort((a, b) => a.lap_start - b.lap_start);
  }, [data]);

  return (
    <div style={{ marginTop: 18 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Tyre Degradation</h3>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ opacity: 0.8, fontSize: 13 }}>Driver</span>
          <select
            value={driver}
            onChange={(e) => setDriver(e.target.value)}
            style={{
              padding: "8px 10px",
              borderRadius: 10,
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.10)",
              color: "white",
            }}
          >
            {drivers.map((d) => (
              <option key={d} value={d} style={{ color: "black" }}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <p style={{ opacity: 0.7, marginTop: 10 }}>Loading degradation…</p>}
      {error && <p style={{ color: "#ff6b6b", marginTop: 10 }}>Error: {error}</p>}

      {!loading && !error && data && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, marginTop: 12 }}>
          {sortedStints.map((s, idx) => {
            const comp = normalizeCompound(s.compound ?? "");
            const dotBg = tyreGradient(comp);
            const slope = s.slope_sec_per_lap;
            const r2 = s.r2;

            return (
              <div
                key={`${s.compound}-${s.lap_start}-${idx}`}
                style={{
                  borderRadius: 14,
                  padding: 12,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      title={s.compound}
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: 999,
                        background: dotBg,
                        boxShadow: `0 0 0 3px rgba(255,255,255,0.06)`,
                      }}
                    />
                    <strong>{s.compound}</strong>
                  </div>
                  <span style={{ opacity: 0.7, fontSize: 12 }}>
                    L{String(s.lap_start)}–L{String(s.lap_end)}
                  </span>
                </div>

                <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.6, opacity: 0.95 }}>
                  <div>
                    <span style={{ opacity: 0.7 }}>Best Lap:</span>{" "}
                    {s.best_lap_s != null ? `${s.best_lap_s.toFixed(3)}s` : "—"}
                  </div>

                  <div>
                    <span style={{ opacity: 0.7 }}>Degradation:</span>{" "}
                    {slope != null ? `${slope.toFixed(3)} sec/lap` : "—"}
                  </div>

                  <div>
                    <span style={{ opacity: 0.7 }}>Fit (R²):</span> {r2 != null ? r2.toFixed(2) : "—"}
                  </div>

                  <div style={{ marginTop: 6, opacity: 0.7, fontSize: 12 }}>{s.message}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && data && data.stints.length === 0 && (
        <p style={{ opacity: 0.7, marginTop: 10 }}>No degradation stints available.</p>
      )}
    </div>
  );
}
