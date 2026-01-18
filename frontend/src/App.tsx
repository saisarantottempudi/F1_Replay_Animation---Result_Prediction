import { useEffect, useMemo, useState } from "react";
import TyreLegend from "./components/TyreLegend";
import TyreStintsTimeline from "./components/TyreStintsTimeline";
import PredictionPanel from "./components/PredictionPanel";
import TyreDegradationPanel from "./components/TyreDegradationPanel";
import StrategyPanel from "./components/StrategyPanel";
import { getTyres } from "./api/f1";
import { getJSON } from "./api/client";

type SeasonList = { seasons: number[] };
type RaceInfo = { round: number; raceName: string; date?: string | null };
type RaceList = { season: number; races: RaceInfo[] };
type SessionList = { season: number; round: number; sessions: string[] };

type Stint = { compound: string; lap_start: number; lap_end: number; pit_lap?: number | null };
type DriverStints = { driver: string; total_laps: number; stints: Stint[] };
type TyresResponse = { season: number; round: number; session: string; drivers: DriverStints[]; message: string };

function isoTodayUTC(): string {
  const d = new Date();
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function currentYearUTC(): number {
  return new Date().getUTCFullYear();
}

function isFutureRace(r: { round: number; date?: string | null }): boolean {
  if (!r || r.round <= 0) return false; // hide testing/non-race
  if (!r.date) return false; // future needs a date
  return r.date >= isoTodayUTC();
}

function isPastOrTodayRace(r: { round: number; date?: string | null }): boolean {
  if (!r || r.round <= 0) return false;
  if (!r.date) return true; // if no date, assume selectable in replay
  return r.date < isoTodayUTC();
}

function pickPredictSeason(seasons: number[], fallback: number): number {
  const y = currentYearUTC();
  if (seasons.includes(y)) return y;
  const le = seasons.filter((s) => s <= y).sort((a, b) => b - a)[0];
  return le ?? fallback;
}

function pickReplaySeason(seasons: number[], fallback: number): number {
  // For replay, default to latest season that is <= current year (avoid defaulting to a future season like 2027)
  const y = currentYearUTC();
  const le = seasons.filter((s) => s <= y).sort((a, b) => b - a)[0];
  return le ?? (seasons.length ? seasons[seasons.length - 1] : fallback);
}

export default function App() {
  const [status, setStatus] = useState("Loading...");
  const [mode, setMode] = useState<"replay" | "predict">("replay");

  const [seasons, setSeasons] = useState<number[]>([]);
  const [season, setSeason] = useState<number>(2024);

  const [races, setRaces] = useState<RaceInfo[]>([]);
  const [round, setRound] = useState<number>(1);

  const [sessions, setSessions] = useState<string[]>([]);
  const [session, setSession] = useState<string>("FP1");

  const [tyres, setTyres] = useState<TyresResponse | null>(null);

  const filteredRaces = useMemo(() => {
    if (!races) return [];
    if (mode === "predict") return races.filter(isFutureRace);
    return races.filter(isPastOrTodayRace);
  }, [races, mode]);

  const selectedRace = useMemo(() => races.find((r) => r.round === round), [races, round]);

  // Load seasons
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading seasons...");
        const s = await getJSON<SeasonList>("/options/seasons");
        const list = (s.seasons ?? []).slice().sort((a, b) => a - b);
        setSeasons(list);

        // Default based on current mode
        const defaultSeason = mode === "predict"
          ? pickPredictSeason(list, season)
          : pickReplaySeason(list, season);

        setSeason(defaultSeason);
        setStatus("Ready");
      } catch (e: any) {
        setStatus(`Error loading seasons: ${e.message}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When switching modes, pick a sensible default season and session
  useEffect(() => {
    if (!seasons.length) return;

    if (mode === "predict") {
      const s = pickPredictSeason(seasons, season);
      setSeason(s);
      setSession("R"); // predictions: Race session only (quali prediction is separate endpoint)
    } else {
      const s = pickReplaySeason(seasons, season);
      setSeason(s);
      // keep session as-is; it will refresh from backend sessions list
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Load races whenever season changes
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading races...");
        const r = await getJSON<RaceList>(`/options/races/${season}`);
        const rr = (r.races ?? []).filter((x: any) => (x?.round ?? 0) > 0);
        setRaces(rr);

        if (mode === "predict") {
          const future = rr.filter(isFutureRace);
          setRound(future[0]?.round ?? rr[0]?.round ?? 1);
        } else {
          setRound(rr[0]?.round ?? 1);
        }

        setStatus("Ready");
      } catch (e: any) {
        setRaces([]);
        setStatus(`Error loading races: ${e.message}`);
      }
    })();
  }, [season, mode]);

  // Load sessions ONLY in replay mode
  useEffect(() => {
    if (mode !== "replay") {
      setSessions(["R"]); // keep something non-empty
      setSession("R");
      return;
    }

    (async () => {
      try {
        setStatus("Loading sessions...");
        const s = await getJSON<SessionList>(`/options/sessions/${season}/${round}`);
        const list = s.sessions ?? [];
        setSessions(list);
        setSession(list[0] ?? "FP1");
        setStatus("Ready");
      } catch (e: any) {
        setSessions([]);
        setStatus(`Error loading sessions: ${e.message}`);
      }
    })();
  }, [season, round, mode]);

  // Load tyres ONLY in replay mode
  useEffect(() => {
    if (mode !== "replay") {
      setTyres(null);
      return;
    }

    setTyres(null);
    setStatus("Loading tyres…");
    getTyres(season, round, session)
      .then((d) => {
        setTyres(d);
        setStatus("Ready");
      })
      .catch(() => {
        setTyres(null);
        setStatus("Ready");
      });
  }, [season, round, session, mode]);

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ marginTop: 0 }}>F1 Replay + Prediction</h1>

      <div style={{ display: "flex", gap: 10, marginTop: 14, marginBottom: 18 }}>
        <button
          onClick={() => setMode("replay")}
          style={{
            padding: "10px 12px",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.10)",
            background: mode === "replay" ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.04)",
            color: "white",
            cursor: "pointer",
          }}
        >
          Replay (Past Race)
        </button>

        <button
          onClick={() => setMode("predict")}
          style={{
            padding: "10px 12px",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.10)",
            background: mode === "predict" ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.04)",
            color: "white",
            cursor: "pointer",
          }}
        >
          Upcoming Predictions
        </button>

        <div style={{ marginLeft: "auto", opacity: 0.7, fontSize: 13, alignSelf: "center" }}>
          Mode: <b>{mode === "replay" ? "Replay" : "Predictions"}</b>
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <TyreLegend />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 16 }}>
        <aside style={{ padding: 16, border: "1px solid #333", borderRadius: 12 }}>
          <h2 style={{ marginTop: 0 }}>Controls</h2>

          <label>Season</label>
          <select
            value={season}
            onChange={(e) => setSeason(Number(e.target.value))}
            style={{ width: "100%", marginTop: 6, marginBottom: 12 }}
          >
            {seasons.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <label>Race</label>
          <select
            value={round}
            onChange={(e) => setRound(Number(e.target.value))}
            style={{ width: "100%", marginTop: 6, marginBottom: 12 }}
            disabled={filteredRaces.length === 0}
          >
            {filteredRaces.length === 0 ? (
              <option value={round}>(No future races for this season)</option>
            ) : (
              filteredRaces.map((r) => (
                <option key={r.round} value={r.round}>
                  Round {r.round} — {r.raceName}
                </option>
              ))
            )}
          </select>

          {mode === "replay" ? (
            <>
              <label>Session</label>
              <select
                value={session}
                onChange={(e) => setSession(e.target.value)}
                style={{ width: "100%", marginTop: 6, marginBottom: 12 }}
              >
                {sessions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </>
          ) : (
            <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 12 }}>
              Predictions mode uses <b>Race</b> + <b>Quali</b> endpoints (no FP1/FP2).
              {/* Sprint support can be added later when we expose a /predict/sprint endpoint. */}
            </div>
          )}

          <div style={{ fontSize: 14, opacity: 0.85 }}>
            <b>Status:</b> {status}
          </div>
        </aside>

        <main style={{ padding: 16, border: "1px solid #333", borderRadius: 12 }}>
          <h2 style={{ marginTop: 0 }}>Selected</h2>
          <div style={{ lineHeight: 1.8 }}>
            <div>
              <b>Season:</b> {season}
            </div>
            <div>
              <b>Round:</b> {round}
            </div>
            <div>
              <b>Race:</b> {selectedRace?.raceName ?? "-"}
              {selectedRace?.date ? <span style={{ opacity: 0.7 }}> ({selectedRace.date})</span> : null}
            </div>
            <div>
              <b>Session:</b> {mode === "predict" ? "R (Predictions)" : session}
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <h3 style={{ marginTop: 0 }}>Predictions</h3>
            <PredictionPanel season={season} round={round} session={mode === "predict" ? "R" : session} />
          </div>

          {mode === "replay" && tyres ? (
            <>
              <div style={{ marginTop: 18 }}>
                <h3 style={{ marginTop: 0 }}>Tyre Stints Timeline</h3>
                <TyreStintsTimeline data={tyres} />
              </div>

              <div style={{ marginTop: 18 }}>
                <TyreDegradationPanel season={season} round={round} session={session} />
              </div>

              <div style={{ marginTop: 18 }}>
                <StrategyPanel season={season} round={round} />
              </div>
            </>
          ) : null}
        </main>
      </div>
    </div>
  );
}
