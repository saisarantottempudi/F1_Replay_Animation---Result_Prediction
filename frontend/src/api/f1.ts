const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export type TyreStint = {
  compound: string;
  lap_start: number;
  lap_end: number;
  pit_lap?: number;
};

export type TyresResponse = {
  season: number;
  round: number;
  session: string;
  drivers: { driver: string; stints: TyreStint[]; total_laps: number }[];
  message: string;
};

export type TyreDegradationStint = {
  compound: string;
  lap_start: number;
  lap_end: number;
  laps_used: number;
  best_lap_s: number | null;
  slope_sec_per_lap: number | null;
  intercept_s?: number;
  r2: number | null;
  message: string;
};

export type TyreDegradationResponse = {
  season: number;
  round: number;
  session: string;
  driver: string;
  stints: TyreDegradationStint[];
  meta: { min_laps: number; quick_quantile: number; note: string };
  message: string;
};

export async function getTyres(season: number, round: number, session: string): Promise<TyresResponse> {
  const res = await fetch(`${API_BASE}/analysis/tyres/${season}/${round}/${session}`);
  if (!res.ok) throw new Error(`Tyres fetch failed: ${res.status}`);
  return res.json();
}

export async function getTyreDegradation(
  season: number,
  round: number,
  session: string,
  driver: string
): Promise<TyreDegradationResponse> {
  const res = await fetch(`${API_BASE}/analysis/tyre-degradation/${season}/${round}/${session}/${driver}`);
  if (!res.ok) throw new Error(`Degradation fetch failed: ${res.status}`);
  return res.json();
}


export type StrategyStint = {
  stint: number | string | null;
  compound: string;
  lap_start: number;
  lap_end: number;
  pace_median_quick_s: number | null;
  deg_slope_sec_per_lap: number | null;
  deg_r2: number | null;
  suggested_pit_window: null | { from_lap: number; to_lap: number; reason: string };
};

export type PitEffect = {
  pit_lap: number;
  pre_window_pace_s: number | null;
  post_window_pace_s: number | null;
  pace_gain_s: number | null;
  label: string;
  note: string;
};

export type StrategyDriver = {
  driver: string;
  pit_laps: number[];
  stints: StrategyStint[];
  pit_effects: PitEffect[];
};

export type StrategyResponse = {
  season: number;
  round: number;
  session: string;
  params: {
    degradation_threshold_sec_per_lap: number;
    quick_quantile: number;
    pit_effect_window_laps: number;
  };
  drivers: StrategyDriver[];
  message: string;
};

export async function getStrategy(season: number, round: number): Promise<StrategyResponse> {
  const res = await fetch(`${API_BASE}/analysis/strategy/${season}/${round}`);
  if (!res.ok) throw new Error(`Strategy fetch failed: ${res.status}`);
  return res.json();
}


export type RacePredRow = {
  driver: string;
  team: string;
  p_win?: number;
  p_top3?: number;
  grid_pos?: number;
  quali_best_s?: number;
};

export type RacePredictionResponse = {
  season: number;
  round: number;
  source: string;
  winner: RacePredRow;
  top3: RacePredRow[];
  all: RacePredRow[];
};

export type QualiPredRow = {
  driver: string;
  team: string;
  p_pole?: number;
  p_top3?: number;
  quali_best_s?: number;
};

export type QualiPredictionResponse = {
  season: number;
  round: number;
  source: string;
  pole: QualiPredRow;
  top3: QualiPredRow[];
  all: QualiPredRow[];
};

export type ChampRowDriver = { driver: string; expected_points: number };
export type ChampRowTeam = { team: string; expected_points: number };

export type ChampionshipFastResponse = {
  season: number;
  mode: string;
  driver_champion: ChampRowDriver[];
  constructor_champion?: ChampRowTeam[];
};


export async function getRacePrediction(season: number, round: number, topk = 3): Promise<RacePredictionResponse> {
  const r = await fetch(`${API_BASE}/predict/race/${season}/${round}?topk=${topk}`);
  if (!r.ok) throw new Error(`Race prediction fetch failed: ${r.status}`);
  return r.json();
}

export async function getQualiPrediction(season: number, round: number, topk = 3): Promise<QualiPredictionResponse> {
  const r = await fetch(`${API_BASE}/predict/quali/${season}/${round}?topk=${topk}`);
  if (!r.ok) throw new Error(`Quali prediction fetch failed: ${r.status}`);
  return r.json();
}

export async function getChampionshipFast(season: number, sims = 5, upto_round?: number): Promise<ChampionshipFastResponse> {
  const q = new URLSearchParams();
  q.set("mode", "fast");
  q.set("sims", String(sims));
  if (upto_round != null) q.set("upto_round", String(upto_round));
  const r = await fetch(`${API_BASE}/predict/championship/${season}?${q.toString()}`);
  if (!r.ok) throw new Error(`Championship fetch failed: ${r.status}`);
  return r.json();
}
