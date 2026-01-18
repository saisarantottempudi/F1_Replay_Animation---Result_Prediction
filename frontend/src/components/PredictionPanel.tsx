import { useEffect, useMemo, useState } from "react";
import { getJSON } from "../api/client";

type RaceRow = {
  driver: string;
  team: string;
  p_win?: number;
  p_top3?: number;
  grid_pos?: number | null;
  quali_best_s?: number | null;
};

type QualiRow = {
  driver: string;
  team: string;
  p_pole?: number;
  p_top3?: number;
  quali_best_s?: number | null;
};

type RaceResp = {
  season: number;
  round: number;
  source: string;
  event?: string;
  winner?: RaceRow;
  top3?: RaceRow[];
  all?: RaceRow[];
  detail?: string;
};

type QualiResp = {
  season: number;
  round: number;
  source: string;
  event?: string;
  pole?: QualiRow;
  top3?: QualiRow[];
  all?: QualiRow[];
  detail?: string;
};

type ChampResp = {
  season: number;
  mode?: string;
  driver_champion?: { driver: string; expected_points?: number; prob?: number }[];
  constructor_champion?: { team: string; expected_points?: number; prob?: number }[];
  detail?: string;
};

function fmtPct(x: any) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "—";
  return `${(Number(x) * 100).toFixed(1)}%`;
}

function fmtNum(x: any) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return "—";
  return String(x);
}

export default function PredictionPanel(props: { season: number; round: number }) {
  const { season, round } = props;

  const [tab, setTab] = useState<"race" | "quali" | "champ">("race");

  const [race, setRace] = useState<RaceResp | null>(null);
  const [quali, setQuali] = useState<QualiResp | null>(null);
  const [champ, setChamp] = useState<ChampResp | null>(null);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const title = useMemo(() => {
    if (tab === "race") return "Race Winner (Top 3)";
    if (tab === "quali") return "Quali Pole (Top 3)";
    return "Championship (Fast)";
  }, [tab]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function run() {
      setLoading(true);
      setErr(null);

      try {
        if (tab === "race") {
          const r = await getJSON<RaceResp>(`/predict/race/${season}/${round}?topk=3`, { signal: controller.signal } as any);
          if (!cancelled) setRace(r);
        } else if (tab === "quali") {
          const q = await getJSON<QualiResp>(`/predict/quali/${season}/${round}?topk=3`, { signal: controller.signal } as any);
          if (!cancelled) setQuali(q);
        } else {
          // keep it light to avoid timeouts
          const c = await getJSON<ChampResp>(`/predict/championship/${season}?mode=fast&sims=10`, { signal: controller.signal } as any);
          if (!cancelled) setChamp(c);
        }
      } catch (e: any) {
        if (!cancelled) setErr(e?.message ?? String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    // 60s max
    const t = setTimeout(() => controller.abort(), 60000);
    run();

    return () => {
      cancelled = true;
      clearTimeout(t);
      controller.abort();
    };
  }, [season, round, tab]);

  const shellStyle: React.CSSProperties = {
    borderRadius: 14,
    padding: 14,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.10)",
  };

  const btn = (active: boolean): React.CSSProperties => ({
    padding: "8px 10px",
    borderRadius: 10,
    border: "1px solid rgba(255,255,255,0.10)",
    background: active ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.05)",
    color: "white",
    cursor: "pointer",
    fontSize: 13,
  });

  return (
    <div style={shellStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
        <strong>{title}</strong>
        <div style={{ opacity: 0.7, fontSize: 12 }}>
          Season {season} • Round {round}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 10, marginBottom: 10, flexWrap: "wrap" }}>
        <button style={btn(tab === "race")} onClick={() => setTab("race")}>Race</button>
        <button style={btn(tab === "quali")} onClick={() => setTab("quali")}>Quali</button>
        <button style={btn(tab === "champ")} onClick={() => setTab("champ")}>Championship</button>
        <div style={{ marginLeft: "auto", opacity: 0.65, fontSize: 12, alignSelf: "center" }}>
          (Prediction mode hides FP sessions)
        </div>
      </div>

      {loading && <p style={{ opacity: 0.7, marginTop: 10 }}>Loading…</p>}
      {err && <p style={{ color: "#ff6b6b", marginTop: 10 }}>Error: {err}</p>}

      {!loading && !err && tab === "race" && race && (
        <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.7 }}>
          <div style={{ opacity: 0.8, marginBottom: 6 }}>
            Source: <b>{race.source}</b>{race.event ? <> • Event: <b>{race.event}</b></> : null}
          </div>

          {race.winner ? (
            <div style={{ marginBottom: 10 }}>
              <div><span style={{ opacity: 0.7 }}>Winner:</span> <b>{race.winner.driver}</b> <span style={{ opacity: 0.8 }}>({race.winner.team})</span></div>
              <div><span style={{ opacity: 0.7 }}>P(win):</span> {fmtPct(race.winner.p_win)} • <span style={{ opacity: 0.7 }}>P(top3):</span> {fmtPct(race.winner.p_top3)}</div>
              <div><span style={{ opacity: 0.7 }}>Grid:</span> {fmtNum(race.winner.grid_pos)} • <span style={{ opacity: 0.7 }}>Quali best:</span> {fmtNum(race.winner.quali_best_s)}</div>
            </div>
          ) : (
            <div style={{ opacity: 0.75 }}>No winner data returned.</div>
          )}

          <div style={{ opacity: 0.8, marginBottom: 6 }}><b>Top 3</b></div>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {(race.top3 ?? []).map((x, i) => (
              <li key={i}>
                <b>{x.driver}</b> <span style={{ opacity: 0.8 }}>({x.team})</span>{" "}
                <span style={{ opacity: 0.75 }}>— P(win) {fmtPct(x.p_win)}, P(top3) {fmtPct(x.p_top3)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {!loading && !err && tab === "quali" && quali && (
        <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.7 }}>
          <div style={{ opacity: 0.8, marginBottom: 6 }}>
            Source: <b>{quali.source}</b>{quali.event ? <> • Event: <b>{quali.event}</b></> : null}
          </div>

          {quali.pole ? (
            <div style={{ marginBottom: 10 }}>
              <div><span style={{ opacity: 0.7 }}>Pole:</span> <b>{quali.pole.driver}</b> <span style={{ opacity: 0.8 }}>({quali.pole.team})</span></div>
              <div><span style={{ opacity: 0.7 }}>P(pole):</span> {fmtPct(quali.pole.p_pole)} • <span style={{ opacity: 0.7 }}>P(top3):</span> {fmtPct(quali.pole.p_top3)}</div>
              <div><span style={{ opacity: 0.7 }}>Quali best:</span> {fmtNum(quali.pole.quali_best_s)}</div>
            </div>
          ) : (
            <div style={{ opacity: 0.75 }}>No pole data returned.</div>
          )}

          <div style={{ opacity: 0.8, marginBottom: 6 }}><b>Top 3</b></div>
          <ol style={{ margin: 0, paddingLeft: 18 }}>
            {(quali.top3 ?? []).map((x, i) => (
              <li key={i}>
                <b>{x.driver}</b> <span style={{ opacity: 0.8 }}>({x.team})</span>{" "}
                <span style={{ opacity: 0.75 }}>— P(pole) {fmtPct(x.p_pole)}, P(top3) {fmtPct(x.p_top3)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {!loading && !err && tab === "champ" && champ && (
        <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.7 }}>
          <div style={{ opacity: 0.8, marginBottom: 6 }}>
            Mode: <b>{champ.mode ?? "fast"}</b>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div style={{ opacity: 0.8, marginBottom: 6 }}><b>Drivers</b></div>
              <ol style={{ margin: 0, paddingLeft: 18 }}>
                {(champ.driver_champion ?? []).slice(0, 5).map((x, i) => (
                  <li key={i}>
                    <b>{x.driver}</b>{" "}
                    <span style={{ opacity: 0.75 }}>
                      {x.prob != null ? `— Prob ${fmtPct(x.prob)}` : x.expected_points != null ? `— Exp pts ${x.expected_points.toFixed(2)}` : ""}
                    </span>
                  </li>
                ))}
              </ol>
            </div>

            <div>
              <div style={{ opacity: 0.8, marginBottom: 6 }}><b>Constructors</b></div>
              <ol style={{ margin: 0, paddingLeft: 18 }}>
                {(champ.constructor_champion ?? []).slice(0, 5).map((x, i) => (
                  <li key={i}>
                    <b>{x.team}</b>{" "}
                    <span style={{ opacity: 0.75 }}>
                      {x.prob != null ? `— Prob ${fmtPct(x.prob)}` : x.expected_points != null ? `— Exp pts ${x.expected_points.toFixed(2)}` : ""}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          <div style={{ marginTop: 10, opacity: 0.65, fontSize: 12 }}>
            Note: This is a fast approximation to avoid timeouts. We’ll add full Monte Carlo later.
          </div>
        </div>
      )}
    </div>
  );
}
