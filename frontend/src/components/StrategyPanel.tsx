import { useEffect, useMemo, useState } from "react";
import { getStrategy } from "../api/f1";
import type { StrategyDriver, StrategyResponse } from "../api/f1";
import { normalizeCompound, tyreGradient } from "../theme/tyres";

type Props = {
  season: number;
  round: number;
  session: string; // should be "R"
};

export default function StrategyPanel({ season, round, session }: Props) {
  const [data, setData] = useState<StrategyResponse | null>(null);
  const [driver, setDriver] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    if (session !== "R") return;
    setLoading(true);
    setErr("");
    setData(null);

    getStrategy(season, round)
      .then((d) => {
        setData(d);
        setDriver(d.drivers?.[0]?.driver ?? "");
      })
      .catch((e) => setErr(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, [season, round, session]);

  const current: StrategyDriver | null = useMemo(() => {
    if (!data || !driver) return null;
    return data.drivers.find((x) => x.driver === driver) ?? null;
  }, [data, driver]);

  const pitWindows = useMemo(() => {
    if (!current) return [];
    return current.stints
      .filter((s) => s.suggested_pit_window)
      .map((s) => ({
        compound: s.compound,
        ...s.suggested_pit_window!,
      }));
  }, [current]);

  if (session !== "R") {
    return (
      <p style={{ opacity: 0.7, marginTop: 12 }}>
        Strategy intelligence is available for <b>Race (R)</b> sessions.
      </p>
    );
  }

  return (
    <div style={{ marginTop: 18 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Strategy Intelligence</h3>

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
            {(data?.drivers ?? []).map((d) => (
              <option key={d.driver} value={d.driver} style={{ color: "black" }}>
                {d.driver}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <p style={{ opacity: 0.7, marginTop: 10 }}>Loading strategy…</p>}
      {err && <p style={{ color: "#ff6b6b", marginTop: 10 }}>Error: {err}</p>}

      {!loading && !err && current && (
        <>
          {/* Pit stops */}
          <div style={{ marginTop: 12, padding: 12, borderRadius: 14, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>Pit Stops</div>
                <div style={{ fontWeight: 700 }}>
                  {current.pit_laps.length > 0 ? current.pit_laps.map((p) => `L${p}`).join(", ") : "—"}
                </div>
              </div>
              <div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>Threshold</div>
                <div style={{ fontWeight: 700 }}>
                  {data?.params?.degradation_threshold_sec_per_lap?.toFixed(3)} sec/lap
                </div>
              </div>
              <div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>Quick-laps Quantile</div>
                <div style={{ fontWeight: 700 }}>{data?.params?.quick_quantile}</div>
              </div>
            </div>
          </div>

          {/* Suggested pit windows */}
          <div style={{ marginTop: 12 }}>
            <h4 style={{ margin: "12px 0 8px 0" }}>Suggested Pit Windows (if degradation is high)</h4>
            {pitWindows.length === 0 ? (
              <p style={{ opacity: 0.7, marginTop: 6 }}>No high-degradation windows detected for this driver.</p>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
                {pitWindows.map((w, idx) => {
                  const comp = normalizeCompound(w.compound ?? "");
                  const bg = tyreGradient(comp);
                  return (
                    <div
                      key={`${w.compound}-${idx}`}
                      style={{
                        borderRadius: 14,
                        padding: 12,
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                        <strong>{w.compound}</strong>
                        <span
                          title={String(comp)}
                          style={{
                            width: 34,
                            height: 10,
                            borderRadius: 999,
                            background: bg,
                            border: "1px solid rgba(255,255,255,0.12)",
                          }}
                        />
                      </div>
                      <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.6 }}>
                        <div>
                          <span style={{ opacity: 0.7 }}>Window:</span> L{w.from_lap} – L{w.to_lap}
                        </div>
                        <div style={{ opacity: 0.7, fontSize: 12, marginTop: 6 }}>{w.reason}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Pit effect (undercut-like) */}
          <div style={{ marginTop: 12 }}>
            <h4 style={{ margin: "12px 0 8px 0" }}>Pit Effect (undercut-like heuristic)</h4>
            {current.pit_effects.length === 0 ? (
              <p style={{ opacity: 0.7, marginTop: 6 }}>No pit effects available.</p>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
                {current.pit_effects.map((pe, idx) => (
                  <div
                    key={`${pe.pit_lap}-${idx}`}
                    style={{
                      borderRadius: 14,
                      padding: 12,
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.08)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong>Pit L{pe.pit_lap}</strong>
                      <span
                        style={{
                          padding: "4px 8px",
                          borderRadius: 999,
                          fontSize: 12,
                          background: pe.label.includes("undercut") ? "rgba(57,211,83,0.18)" : "rgba(255,255,255,0.08)",
                          border: "1px solid rgba(255,255,255,0.10)",
                        }}
                      >
                        {pe.label}
                      </span>
                    </div>

                    <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.6 }}>
                      <div>
                        <span style={{ opacity: 0.7 }}>Pre:</span>{" "}
                        {pe.pre_window_pace_s != null ? `${pe.pre_window_pace_s.toFixed(3)}s` : "—"}
                      </div>
                      <div>
                        <span style={{ opacity: 0.7 }}>Post:</span>{" "}
                        {pe.post_window_pace_s != null ? `${pe.post_window_pace_s.toFixed(3)}s` : "—"}
                      </div>
                      <div>
                        <span style={{ opacity: 0.7 }}>Gain:</span>{" "}
                        {pe.pace_gain_s != null ? `${pe.pace_gain_s.toFixed(3)}s` : "—"}
                      </div>
                      <div style={{ opacity: 0.7, fontSize: 12, marginTop: 6 }}>{pe.note}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
