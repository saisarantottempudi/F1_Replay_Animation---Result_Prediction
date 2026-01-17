import { useEffect, useMemo, useState } from "react";
import TyreLegend from "./components/TyreLegend";
import TyreStintsTimeline from "./components/TyreStintsTimeline";
import { getJSON } from "./api/client";

type SeasonList = { seasons: number[] };
type RaceInfo = { round: number; raceName: string };
type RaceList = { season: number; races: RaceInfo[] };
type SessionList = { season: number; round: number; sessions: string[] };

type Stint = { compound: string; lap_start: number; lap_end: number; pit_lap?: number | null };
type DriverStints = { driver: string; total_laps: number; stints: Stint[] };
type TyresResponse = { season: number; round: number; session: string; drivers: DriverStints[]; message: string };

export default function App() {
  const [status, setStatus] = useState("Loading...");
  const [seasons, setSeasons] = useState<number[]>([]);
  const [season, setSeason] = useState<number>(2024);

  const [races, setRaces] = useState<RaceInfo[]>([]);
  const [round, setRound] = useState<number>(1);

  const [sessions, setSessions] = useState<string[]>([]);
  const [tyres, setTyres] = useState<TyresResponse | null>(null);
  const [session, setSession] = useState<string>("FP1");

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
        setRaces(r.races);
        setRound(r.races[0]?.round ?? 1);
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

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ marginTop: 0 }}>F1 Replay + Prediction</h1>

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
            {races.map((r) => (
              <option key={r.round} value={r.round}>
                Round {r.round} — {r.raceName}
              </option>
            ))}
          </select>

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
          </div>

          <div style={{ marginTop: 14, opacity: 0.85 }}>
            Next: we’ll render the <b>Tyre Stints Timeline</b> with these colors.
          </div>
        </main>
      </div>
    </div>
  );
}
