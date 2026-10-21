// Shape of public/data.json, written by export_data.py.

export type Bands = { p5: number[]; p25: number[]; p50: number[]; p75: number[]; p95: number[] };

export type BacktestOrigin = {
  origin: string;
  bands: Bands;
  actual: number[];
  chance: number | null;
  crossed: boolean;
};

export type Backtest = {
  origins: BacktestOrigin[];
  mae: number[];                 // average miss per 1,000, by weeks ahead
  brier: number | null;          // surge-call score, 0 is perfect
  coverage: number | null;       // share of actual values inside the 90% range
  crps: number | null;           // CRPS per 1,000, averaged over horizons 1-4 (src/compare.py)
  warningWeeks: number;          // weeks of warning before the season's surge crossing
  crossing: string | null;
};

export type Model = {
  id: string;
  name: string;
  kind: "Baseline" | "Statistical" | "AI";
  about: string;
  owner: string;
  folds: Record<string, Backtest | null>;
  sample: boolean;               // illustrative results until the real ones are saved
  live: { chance: number[] | null; mid4: number } | null;
};

export type Surge = {
  label: string;
  start: string | null;
  end: string | null;
  startWeek: number | null;
  endWeek: number | null;
  peak: string;
  peakWeek: number;
  peakValue: number;
  weeksAbove: number;
};

export type Season = { season: number; label: string; points: [number, number][] };

export type Dashboard = {
  updated: string;
  lines: { surge: number; season: number };
  now: {
    value: number;
    oneIn: number | null;
    trend: "rising" | "falling" | "steady";
    level: 0 | 1 | 2 | 3;
    levelName: string;
    chance: number[] | null;
    model: string;
  };
  recent: { date: string; v: number }[];
  weekly: { date: string; v: number }[];
  forecast: Bands & { dates: string[] };
  layers: { date: string; lo: number | null; mid: number | null; hi: number | null; last: number | null }[];
  stats: {
    medianPeak: number;
    maxPeak: number;
    medianWeeksAbove: number;
    lagToPeak: number;
    weeksToTypical: number;
    earliestCrossing: string;
    leadMedian: number | null;
    leadMin: number | null;
    leadMax: number | null;
    high4: number;
    mid4: number;
    weeksAboveSoFar: number;
    seasonsCrossed: number;
    seasonsTotal: number;
    normalNow: number | null;
    vsNormal: number | null;
    posNow: number;
    posPeak: number;
    peakDate: string;
    oneInPeak: number | null;
    weeksToEarliest: number;
    statesAbove: number;
    statesTotal: number;
    topRiser: { state: string; v: number; change: number } | null;
  };
  states: { epiweek: number; states: { state: string; epiweek: number; v: number; change: number | null }[] } | null;
  seasons: Season[];
  currentSeason: number;
  surges: Surge[];
  typicalCrossing: string;
  models: Model[];
  mainFold: string;
};

export async function loadDashboard(): Promise<Dashboard> {
  const res = await fetch("./data.json");
  if (!res.ok) throw new Error(`data.json returned ${res.status}`);
  return res.json();
}

// Dates arrive as YYYY-MM-DD; parse as local dates so labels don't shift a day.
export const toDate = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};

export const fmtDay = (s: string, opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }) =>
  toDate(s).toLocaleDateString("en-US", opts);

export const addWeeks = (s: string, n: number) => {
  const d = toDate(s);
  d.setDate(d.getDate() + 7 * n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const pct = (p: number) => `${Math.round(p * 100)}%`;

export const LEVELS = [
  { name: "Quiet", color: "var(--quiet)" },
  { name: "Elevated", color: "var(--elevated)" },
  { name: "Surge watch", color: "var(--watch)" },
  { name: "Surge", color: "var(--surge)" },
] as const;

export const STATE_NAMES: Record<string, string> = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado", CT: "Connecticut",
  DE: "Delaware", DC: "District of Columbia", FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois",
  IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland",
  MA: "Massachusetts", MI: "Michigan", MN: "Minnesota", MS: "Mississippi", MO: "Missouri", MT: "Montana",
  NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York",
  NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon", PA: "Pennsylvania",
  RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah",
  VT: "Vermont", VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
};
