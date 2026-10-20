import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { geoPath } from "d3-geo";
import { scaleThreshold } from "d3-scale";
import { feature, mesh } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import us from "us-atlas/states-albers-10m.json";
import { TrendDown, TrendUp } from "@phosphor-icons/react";
import type { Dashboard } from "../data";

// FIPS code -> postal code, for joining the map to the state data
const FIPS: Record<string, string> = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
  "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
  "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT",
  "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
  "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
  "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
};

const STEPS = [0.25, 0.5, 1, 2, 4];
const BLUES = ["#e3eef9", "#bcd7f0", "#8ab8e3", "#4f8fd0", "#1c63b7", "#0d3f7a"];
const color = scaleThreshold<number, string>().domain(STEPS).range(BLUES);

type Topo = Topology<{ states: GeometryCollection<{ name: string }>; nation: GeometryCollection }>;

export function StateMap({ data }: { data: Dashboard }) {
  const reduce = useReducedMotion();
  const [hover, setHover] = useState<string | null>(null);
  const snap = data.states;
  const topo = us as unknown as Topo;
  const shapes = useMemo(() => feature(topo, topo.objects.states).features, [topo]);
  const borders = useMemo(() => mesh(topo, topo.objects.states, (a, b) => a !== b), [topo]);
  const path = geoPath();

  if (!snap) return null;
  const byState = Object.fromEntries(snap.states.map((s) => [s.state, s]));
  const nat = data.now.value;
  const above = snap.states.filter((s) => s.v > nat).length;
  const rising = [...snap.states].filter((s) => s.change !== null).sort((a, b) => b.change! - a.change!).slice(0, 5);
  const names = Object.fromEntries(shapes.map((f) => [FIPS[String(f.id)], f.properties.name]));
  const h = hover ? byState[hover] : null;

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 md:px-8">
      <h2 className="text-3xl font-bold tracking-tight">Where flu is rising first</h2>
      <p className="mt-2 max-w-[62ch] text-muted">
        Flu visits per 1,000 by state. {above} of {snap.states.length} reporting states are above the national level of {nat.toFixed(1)}.
      </p>

      <div className="mt-8 grid gap-10 lg:grid-cols-[8fr_4fr]">
        <figure className="relative">
          <svg viewBox="0 0 975 610" className="w-full" role="img" aria-label="Map of flu visits per 1,000 by state">
            <defs>
              <pattern id="nodata" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" fill="#f4f7fa" />
                <line x1="0" y1="0" x2="0" y2="6" stroke="#d3dde7" strokeWidth="2" />
              </pattern>
            </defs>
            {shapes.map((f, i) => {
              const code = FIPS[String(f.id)];
              const s = byState[code];
              return (
                <motion.path key={code ?? i} d={path(f) ?? ""} fill={s ? color(s.v) : "url(#nodata)"}
                             stroke={hover === code ? "var(--ink)" : "none"} strokeWidth={2}
                             initial={reduce ? false : { opacity: 0 }} whileInView={{ opacity: 1 }}
                             viewport={{ once: true, amount: 0.3 }}
                             transition={{ duration: 0.5, delay: reduce ? 0 : (s ? Math.min(s.v, 4) : 0) * 0.12 }}
                             onPointerEnter={() => setHover(code)} onPointerLeave={() => setHover(null)}>
                  <title>{s ? `${f.properties.name}: ${s.v.toFixed(1)} per 1,000` : `${f.properties.name}: no data`}</title>
                </motion.path>
              );
            })}
            <path d={path(borders) ?? ""} fill="none" stroke="#fff" strokeWidth={1} strokeLinejoin="round" pointerEvents="none" />
          </svg>
          {hover && (
            <div className="pointer-events-none absolute top-0 left-0 rounded-xl bg-ink px-3 py-2 text-sm text-bg tabular">
              <div className="font-semibold">{names[hover]}</div>
              {h ? (
                <>
                  <div>{h.v.toFixed(1)} per 1,000 visits</div>
                  {h.change !== null && <div className="opacity-75">{h.change >= 0 ? "+" : ""}{h.change.toFixed(1)} vs. 3 weeks ago</div>}
                </>
              ) : <div className="opacity-75">Not reported this month</div>}
            </div>
          )}
          <figcaption className="mt-3 flex flex-wrap items-center gap-x-1 gap-y-2 text-xs text-muted">
            <span className="mr-2">Flu visits per 1,000</span>
            {BLUES.map((c, i) => (
              <span key={c} className="flex items-center gap-1">
                <i className="h-3 w-7 rounded-sm" style={{ background: c }} />
                <span className="mr-2 tabular">{i === 0 ? `<${STEPS[0]}` : i === BLUES.length - 1 ? `${STEPS[i - 1]}+` : `${STEPS[i - 1]}`}</span>
              </span>
            ))}
            <span className="flex items-center gap-1"><i className="h-3 w-7 rounded-sm" style={{ background: "repeating-linear-gradient(45deg, #f4f7fa 0 3px, #d3dde7 3px 5px)" }} />No data</span>
          </figcaption>
        </figure>

        <div>
          <h3 className="font-semibold">Rising fastest over 3 weeks</h3>
          <ol className="mt-4 space-y-3">
            {rising.map((s, i) => (
              <li key={s.state} className="flex items-center gap-3">
                <span className="w-5 text-sm text-muted tabular">{i + 1}</span>
                <span className="flex-1 font-medium">{names[s.state] ?? s.state}</span>
                <span className="text-sm text-muted tabular">{s.v.toFixed(1)}</span>
                <span className={`flex w-16 items-center justify-end gap-1 text-sm font-semibold tabular ${s.change! >= 0 ? "text-surge" : "text-quiet"}`}>
                  {s.change! >= 0 ? <TrendUp size={14} weight="bold" aria-hidden /> : <TrendDown size={14} weight="bold" aria-hidden />}
                  {s.change! >= 0 ? "+" : ""}{s.change!.toFixed(1)}
                </span>
              </li>
            ))}
          </ol>
          <p className="mt-6 text-sm text-muted">
            Same measure as the national series, from CDC FluView by state. Some states don't report to ILINet and show as no data.
            The forecast itself is national.
          </p>
        </div>
      </div>
    </section>
  );
}
