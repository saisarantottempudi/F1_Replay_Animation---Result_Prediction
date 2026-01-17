import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { getJSON } from "./api/client";

type SeasonList = { seasons: number[] };
type RaceInfo = { round: number; raceName: string };
type RaceList = { season: number; races: RaceInfo[] };
type SessionList = { season: number; round: number; sessions: string[] };

type WeatherPoint = {
  Time: string;
  AirTemp: number;
  TrackTemp: number;
  Rainfall: boolean;
  WindSpeed: number;
  WindDirection: number;
};

type TEIPoint = { t_s: number; median_lap_s: number; tei: number };

type WeatherTEIResponse = {
  season: number;
  round: number;
  session: string;
  weather: WeatherPoint[];
  tei: TEIPoint[];
  message: string;
};

function parseTimeToSeconds(timeStr: string): number {
  // FastF1 format typically: "0 days 00:10:43.504000"
  // We'll extract HH:MM:SS(.micro) and convert to seconds
  const parts = timeStr.split(" ");
  const hms = parts[parts.length - 1]; // "00:10:43.504000"
  const [hh, mm, ssMicro] = hms.split(":");
  const ss = Number(ssMicro.split(".")[0]);
  return Number(hh) * 3600 + Number(mm) * 60 + ss;
}

export default function App() {
  const [status, setStatus] = useState("Loading...");
  const [seasons, setSeasons] = useState<number[]>([]);
  const [season, setSeason] = useState<number>(2025);

  const [races, setRaces] = useState<RaceInfo[]>([]);
  const [round, setRound] = useState<number>(1);

  const [sessions, setSessions] = useState<string[]>([]);
  const [session, setSession] = useState<string>("R");

  const [analysis, setAnalysis] = useState<WeatherTEIResponse | null>(null);

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
      } catch (e: any) {
        setStatus(`Error: ${e.message}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load races for season
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

  // Load sessions for (season, round)
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading sessions...");
        const s = await getJSON<SessionList>(`/options/sessions/${season}/${round}`);
        setSessions(s.sessions);

        const defaultSession = s.sessions.includes("R")
          ? "R"
          : (s.sessions[0] ?? "R");
        setSession(defaultSession);
      } catch (e: any) {
        setStatus(`Error: ${e.message}`);
      }
    })();
  }, [season, round]);

  // Load Weather+TEI analysis for (season, round, session)
  useEffect(() => {
    (async () => {
      try {
        setStatus("Loading Weather + TEI...");
        setAnalysis(null);
        const a = await getJSON<WeatherTEIResponse>(
          `/analysis/weather-evolution/${season}/${round}/${session}`
        );
        setAnalysis(a);
        setStatus(a.message || "Ready");
      } catch (e: any) {
        setStatus(`Error: ${e.message}`);
      }
    })();
  }, [season, round, session]);

  const teiX = useMemo(() => (analysis?.tei ?? []).map((p) => p.t_s / 60), [analysis]);
  const teiY = useMemo(() => (analysis?.tei ?? []).map((p) => p.tei), [analysis]);

  const wX = useMemo(() => (analysis?.weather ?? []).map((p) => parseTimeToSeconds(p.Time) / 60), [analysis]);
  const trackTemp = useMemo(() => (analysis?.weather ?? []).map((p) => p.TrackTemp), [analysis]);
  const rain = useMemo(() => (analysis?.weather ?? []).map((p) => p.Rainfall), [analysis]);

  const rainMarkersX = useMemo(
    () => wX.filter((_, i) => rain[i] === true),
    [wX, rain]
  );

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
          <h2 style={{ marginTop: 0 }}>Weather + Track Evolution</h2>

          <p style={{ marginTop: 0, opacity: 0.9 }}>
            <b>Season:</b> {season} &nbsp;|&nbsp;
            <b>Round:</b> {round} &nbsp;|&nbsp;
            <b>Race:</b> {selectedRace?.raceName ?? "-"} &nbsp;|&nbsp;
            <b>Session:</b> {session}
          </p>

          <div style={{ height: 420 }}>
            <Plot
              data={[
                {
                  x: teiX,
                  y: teiY,
                  type: "scatter",
                  mode: "lines+markers",
                  name: "TEI (Track Evolution Index)",
                  yaxis: "y1",
                },
                {
                  x: wX,
                  y: trackTemp,
                  type: "scatter",
                  mode: "lines",
                  name: "Track Temp (°C)",
                  yaxis: "y2",
                },
                {
                  x: rainMarkersX,
                  y: rainMarkersX.map(() => 1), // just to show markers; scaled on y1
                  type: "scatter",
                  mode: "markers",
                  name: "Rain detected",
                  yaxis: "y1",
                },
              ]}
              layout={{
                autosize: true,
                margin: { l: 50, r: 50, t: 20, b: 40 },
                xaxis: { title: "Session time (minutes)" },
                yaxis: { title: "TEI (higher = faster track)", side: "left" },
                yaxis2: { title: "Track Temp (°C)", overlaying: "y", side: "right" },
                legend: { orientation: "h" },
              }}
              style={{ width: "100%", height: "100%" }}
              config={{ displaylogo: false, responsive: true }}
            />
          </div>

          <div style={{ marginTop: 12, opacity: 0.85 }}>
            Next: we will compute a stronger TEI (flag-aware + driver-normalized) and use this in Winner Prediction & Degradation modelling.
          </div>
        </main>
      </div>
    </div>
  );
}
