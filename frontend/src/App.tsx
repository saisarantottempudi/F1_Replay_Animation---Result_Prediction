import { useEffect, useMemo, useState } from "react";
import { getJSON } from "./api/client";

type SeasonList = { seasons: number[] };
type RaceInfo = { round: number; raceName: string };
type RaceList = { season: number; races: RaceInfo[] };
type SessionList = { season: number; round: number; sessions: string[] };

export default function App() {
  const [status, setStatus] = useState("Loading...");
  const [seasons, setSeasons] = useState<number[]>([]);
  const [season, setSeason] = useState<number>(2025);

  const [races, setRaces] = useState<RaceInfo[]>([]);
  const [round, setRound] = useState<number>(1);

  const [sessions, setSessions] = useState<string[]>([]);
  const [session, setSession] = useState<string>("R");

  const selectedRace = useMemo(
    () => races.find((r) => r.round === round),
    [races, round]
  );

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
      } catch (e: any) {
        setStatus(`Error: ${e.message}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading races...");
        const r = await getJSON<RaceList>(`/options/races/${season}`);
        setRaces(r.races);
        setRound(r.races[0]?.round ?? 1);
      } catch (e: any) {
        setStatus(`Error: ${e.message}`);
      }
    })();
  }, [season]);

  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading sessions...");
        const s = await getJSON<SessionList>(`/options/sessions/${season}/${round}`);
        setSessions(s.sessions);

        // pick a sensible default: Race if available
        const defaultSession = s.sessions.includes("R")
          ? "R"
          : (s.sessions[0] ?? "R");
        setSession(defaultSession);

        setStatus("Ready");
      } catch (e: any) {
        setStatus(`Error: ${e.message}`);
      }
    })();
  }, [season, round]);

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ marginTop: 0 }}>F1 Replay + Prediction</h1>

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
              <option key={s} value={s}>{s}</option>
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
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <div style={{ fontSize: 14, opacity: 0.85 }}>
            <b>Status:</b> {status}
          </div>
        </aside>

        <main style={{ padding: 16, border: "1px solid #333", borderRadius: 12 }}>
          <h2 style={{ marginTop: 0 }}>Selected</h2>
          <p style={{ margin: 0 }}>
            <b>Season:</b> {season}<br />
            <b>Round:</b> {round}<br />
            <b>Race:</b> {selectedRace?.raceName ?? "-"}<br />
            <b>Session:</b> {session}
          </p>

          <hr style={{ margin: "16px 0", borderColor: "#333" }} />

          <div style={{ opacity: 0.85 }}>
            Next: Weather + Track Evolution timeline for the selected session.
          </div>
        </main>
      </div>
    </div>
  );
}
