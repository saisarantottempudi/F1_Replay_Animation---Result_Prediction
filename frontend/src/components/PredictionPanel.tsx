import { useEffect, useMemo, useState } from "react";

type Props = {
  season: number;
  round: number;
  session: string; // FP1/FP2/FP3/Q/R etc.
};

type RaceRow = { driver: string; team: string; p_win: number; p_top3: number; grid_pos?: number; quali_best_s?: number };
type QualiRow = { driver: string; team: string; p_pole: number; p_top3: number; quali_best_s?: number };

type RacePred = {
  season: number;
  round: number;
  source: string;
  winner: RaceRow;
  top3: RaceRow[];
  all?: RaceRow[];
};

type QualiPred = {
  season: number;
  round: number;
  source: string;
  pole: QualiRow;
  top3: QualiRow[];
  all?: QualiRow[];
};

type ChampPred = {
  season: number;
  mode: string;
  driver_champion: { driver: string; expected_points: number }[];
  constructor_champion?: { team: string; expected_points: number }[];
};

function apiBase() {
  // Prefer env var, fallback to localhost API
  // (works with Vite)
  // @ts-ignore
  return (import.meta?.env?.VITE_API_URL as string) || "http://127.0.0.1:8000";
}

async function fetchJson<T>(url: string, timeoutMs = 25000): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      signal: ctrl.signal,
      headers: { "Accept": "application/json" },
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText}${txt ? ` — ${txt}` : ""}`);
    }

    return (await res.json()) as T;
  } catch (e: any) {
    if (e?.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
    }
    throw e;
  } finally {
    clearTimeout(t);
  }
}

function fmtPct(x: number) {
  if (x == null || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(1)}%`;
}

export default function PredictionPanel({ season, round, session }: Props) {
  const base = useMemo(() => apiBase(), []);

  const [race, setRace] = useState<RacePred | null>(null);
  const [quali, setQuali] = useState<QualiPred | null>(null);
  const [champ, setChamp] = useState<ChampPred | null>(null);

  const [loadingRace, setLoadingRace] = useState(false);
  const [loadingQuali, setLoadingQuali] = useState(false);
  const [loadingChamp, setLoadingChamp] = useState(false);

  const [errRace, setErrRace] = useState("");
  const [errQuali, setErrQuali] = useState("");
  const [errChamp, setErrChamp] = useState("");

  // Race + Quali (fast) -> always load
  useEffect(() => {
    let alive = true;

    setLoadingRace(true);
    setErrRace("");
    setRace(null);

    fetchJson<RacePred>(`${base}/predict/race/${season}/${round}?topk=3`, 60000)
      .then((d) => alive && setRace(d))
      .catch((e) => alive && setErrRace(String(e?.message ?? e)))
      .finally(() => alive && setLoadingRace(false));

    return () => { alive = false; };
  }, [base, season, round]);

  useEffect(() => {
    let alive = true;

    setLoadingQuali(true);
    setErrQuali("");
    setQuali(null);

    fetchJson<QualiPred>(`${base}/predict/quali/${season}/${round}?topk=3`, 60000)
      .then((d) => alive && setQuali(d))
      .catch((e) => alive && setErrQuali(String(e?.message ?? e)))
      .finally(() => alive && setLoadingQuali(false));

    return () => { alive = false; };
  }, [base, season, round]);

  // Championship -> ONLY when session is R (Race)
  useEffect(() => {
    let alive = true;

    setChamp(null);
    setErrChamp("");

    if (session !== "R") {
      setLoadingChamp(false);
      return () => { alive = false; };
    }

    setLoadingChamp(true);

    // Fast mode: small sims; still can take ~25–30s sometimes
    fetchJson<ChampPred>(`${base}/predict/championship/${season}?mode=fast&sims=5`, 45000)
      .then((d) => alive && setChamp(d))
      .catch((e) => alive && setErrChamp(String(e?.message ?? e)))
      .finally(() => alive && setLoadingChamp(false));

    return () => { alive = false; };
  }, [base, season, session]);

  return (
    <div style={{ marginTop: 18 }}>
      <h3 style={{ margin: 0, marginBottom: 10 }}>Predictions</h3>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
        {/* Race */}
        <div style={{ borderRadius: 14, padding: 12, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
            <strong>Race Winner</strong>
            <span style={{ opacity: 0.7, fontSize: 12 }}>Top 3</span>
          </div>

          {loadingRace && <p style={{ opacity: 0.7, marginTop: 10 }}>Loading…</p>}
          {errRace && <p style={{ color: "#ff6b6b", marginTop: 10 }}>Error: {errRace}</p>}

          {!loadingRace && !errRace && race && (
            <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.7 }}>
              <div style={{ marginBottom: 8 }}>
                <div><span style={{ opacity: 0.7 }}>Winner:</span> <b>{race.winner.driver}</b> <span style={{ opacity: 0.8 }}>({race.winner.team})</span></div>
                <div><span style={{ opacity: 0.7 }}>P(win):</span> {fmtPct(race.winner.p_win)} • <span style={{ opacity: 0.7 }}>P(top3):</span> {fmtPct(race.winner.p_top3)}</div>
              </div>

              {race.top3.map((r, i) => (
                <div key={r.driver} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div>{i + 1}. <b>{r.driver}</b> <span style={{ opacity: 0.8 }}>({r.team})</span></div>
                  <div style={{ opacity: 0.9 }}>{fmtPct(r.p_win)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quali */}
        <div style={{ borderRadius: 14, padding: 12, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
            <strong>Quali Pole</strong>
            <span style={{ opacity: 0.7, fontSize: 12 }}>Top 3</span>
          </div>

          {loadingQuali && <p style={{ opacity: 0.7, marginTop: 10 }}>Loading…</p>}
          {errQuali && <p style={{ color: "#ff6b6b", marginTop: 10 }}>Error: {errQuali}</p>}

          {!loadingQuali && !errQuali && quali && (
            <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.7 }}>
              <div style={{ marginBottom: 8 }}>
                <div><span style={{ opacity: 0.7 }}>Pole:</span> <b>{quali.pole.driver}</b> <span style={{ opacity: 0.8 }}>({quali.pole.team})</span></div>
                <div><span style={{ opacity: 0.7 }}>P(pole):</span> {fmtPct(quali.pole.p_pole)} • <span style={{ opacity: 0.7 }}>P(top3):</span> {fmtPct(quali.pole.p_top3)}</div>
              </div>

              {quali.top3.map((q, i) => (
                <div key={q.driver} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div>{i + 1}. <b>{q.driver}</b> <span style={{ opacity: 0.8 }}>({q.team})</span></div>
                  <div style={{ opacity: 0.9 }}>{fmtPct(q.p_pole)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Championship */}
        <div style={{ borderRadius: 14, padding: 12, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
            <strong>Championship</strong>
            <span style={{ opacity: 0.7, fontSize: 12 }}>{session === "R" ? "Race only" : "Select R"}</span>
          </div>

          {session !== "R" && (
            <p style={{ opacity: 0.7, marginTop: 10 }}>
              Championship projection loads only for <b>Race (R)</b> session.
            </p>
          )}

          {session === "R" && loadingChamp && <p style={{ opacity: 0.7, marginTop: 10 }}>Computing (fast)…</p>}
          {session === "R" && errChamp && <p style={{ color: "#ff6b6b", marginTop: 10 }}>Error: {errChamp}</p>}

          {session === "R" && !loadingChamp && !errChamp && champ && (
            <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.7 }}>
              <div style={{ opacity: 0.8, marginBottom: 6 }}>Driver (expected points)</div>
              {champ.driver_champion.slice(0, 5).map((d, i) => (
                <div key={d.driver} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div>{i + 1}. <b>{d.driver}</b></div>
                  <div style={{ opacity: 0.9 }}>{d.expected_points.toFixed(2)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
