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

function isoTodayUTC(): string {
  // Compare using YYYY-MM-DD strings (safe for ISO dates)
  const d = new Date();
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function isFutureRace(r: { round: number; date?: string | null }): boolean {
  // hide testing / non-race items
  if (!r || r.round <= 0) return false;
  if (!r.date) return false;
  return r.date >= isoTodayUTC();
}

function isPastOrTodayRace(r: { round: number; date?: string | null }): boolean {
  if (!r || r.round <= 0) return false;
  if (!r.date) return true; // if no date, assume available
  return r.date < isoTodayUTC();
}
type RaceList = { season: number; races: RaceInfo[] };
type SessionList = { season: number; round: number; sessions: string[] };

type Stint = { compound: string; lap_start: number; lap_end: number; pit_lap?: number | null };
type DriverStints = { driver: string; total_laps: number; stints: Stint[] };
type TyresResponse = { season: number; round: number; session: string; drivers: DriverStints[]; message: string };

export default function App() {
  const [status, setStatus] = useState("Loading...");
  const [mode, setMode] = useState<"replay" | "predict">("replay");
  const [seasons, setSeasons] = useState<number[]>([]);
  const [season, setSeason] = useState<number>(2024);

  const [races, setRaces] = useState<RaceInfo[]>([]);
  const [round, setRound] = useState<number>(1);

  const [sessions, setSessions] = useState<string[]>([]);
  const [tyres, setTyres] = useState<TyresResponse | null>(null);
  const [session, setSession] = useState<string>("FP1");

  const maxSeasonAvailable = useMemo(() => (seasons.length ? Math.max(...seasons) : season), [seasons, season]);

  
  const filteredRaces = useMemo(() => {
    if (!races) return [];
    if (mode === "predict") {
      return races.filter(isFutureRace);
    }
    return races.filter(isPastOrTodayRace);
  }, [races, mode]);


  // Auto-select next future race when entering prediction mode
  useEffect(() => {
    if (mode !== "predict") return;
    if (!filteredRaces || filteredRaces.length === 0) return;

    const next = filteredRaces[0];
    if (next && next.round && next.round !== round) {
      setRound(next.round);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, filteredRaces.length]);

const selectedRace = useMemo(
    () => races.find((r) => r.round === round),
    [races, round]
  );

  // Load seasons
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading seasons...");
        const s = await getJSON<SeasonList>("/options/seasons");
        setSeasons(s.seasons);
        const defaultSeason = s.seasons.includes(season)
          ? season
          : s.seasons[s.seasons.length - 1];
        setSeason(defaultSeason);
        setStatus("Ready");
      } catch (e: any) {
        setStatus(`Error loading seasons: ${e.message}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load races
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading races...");
        const r = await getJSON<RaceList>(`/options/races/${season}`);
        const rr = (r.races ?? []).filter((x:any) => (x?.round ?? 0) > 0);
        setRaces(rr);
        setRound(rr[0]?.round ?? 1);
        setStatus("Ready");
      } catch (e: any) {
        setStatus(`Error loading races: ${e.message}`);
      }
    })();
  }, [season]);

  // Load sessions
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading sessions...");
        const s = await getJSON<SessionList>(`/options/sessions/${season}/${round}`);
        setSessions(s.sessions);
        setSession(s.sessions[0] ?? "FP1");
        setStatus("Ready");
      } catch (e: any) {
        setStatus(`Error loading sessions: ${e.message}`);
      }
    })();
  }, [season, round]);

  // Load tyres stints for (season, round, session)
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading tyres...");
        setTyres(null);
        const t = await getJSON<TyresResponse>(`/analysis/tyres/${season}/${round}/${session}`);
        setTyres(t);
        setStatus("Ready");
      } catch (e: any) {
        setStatus(`Error loading tyres: ${e.message}`);
      }
    })();
  }, [season, round, session]);

  
  useEffect(() => {
    // Tyre stints are meaningful for Race (R). We still allow fetching for others.
    setTyres(null);
    setStatus("Loading tyres…");
    getTyres(season, round, session)
      .then((d) => {
        setTyres(d);
        setStatus("Ready");
      })
      .catch((e) => {
        setTyres(null);
        setStatus("Ready");
        console.error(e);
      });
  }, [season, round, session]);

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
            onClick={() => {
              setMode("predict");
              setSession("R");
            }}
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
          >
            {filteredRaces.map((r) => (
              <option key={r.round} value={r.round}>
                Round {r.round} — {r.raceName}
              </option>
            ))}
          </select>

          <label>Session</label>
          <select
            value={session}
            onChange={(e) => setSession(e.target.value)}
            disabled={mode === "predict"}
            style={{ width: "100%", marginTop: 6, marginBottom: 12 }}
          >
            {sessions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <div style={{ fontSize: 14, opacity: 0.85 }}>
            <b>Status:</b> {status}
          </div>
        </aside>

        <main style={{ padding: 16, border: "1px solid #333", borderRadius: 12 }}>
          <h2 style={{ marginTop: 0 }}>Selected</h2>
          <div style={{ lineHeight: 1.8 }}>
            <div><b>Season:</b> {season}</div>
            <div><b>Round:</b> {round}</div>
            <div><b>Race:</b> {selectedRace?.raceName ?? "-"}</div>
            <div><b>Session:</b> {session}</div>

            <PredictionPanel season={season} round={round} session={session} />

          </div>

          <div style={{ marginTop: 14, opacity: 0.85 }}>
            {tyres && tyres.drivers.length > 0 && (
              <>
                <h3 style={{ marginTop: 18 }}>Tyre Stints Timeline</h3>
                <TyreStintsTimeline drivers={tyres.drivers} />

            {session === "R" ? (
              <>
                <h3 style={{ marginTop: 18 }}>Tyre Degradation (per driver)</h3>
                <TyreDegradationPanel
                  season={season}
                  round={round}
                  session={session}
                  drivers={(tyres?.drivers ?? []).map((d: any) => d.driver)}
                />
              </>
            ) : (
              <p style={{ opacity: 0.7, marginTop: 12 }}>
                Tyre degradation is available for <b>Race (R)</b> sessions.
              </p>
            )}
            {session === "R" && (
              <TyreDegradationPanel
                season={season}
                round={round}
                session={session}
                drivers={tyres.drivers.map((d: any) => d.driver)}
              />
            )}
              </>
            )}

            {tyres && tyres.drivers.length === 0 && (
              <p style={{ opacity: 0.7, marginTop: 12 }}>
                Tyre stints are not available for this session.
              </p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
