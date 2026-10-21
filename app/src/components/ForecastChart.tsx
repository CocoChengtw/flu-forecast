import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { scaleLinear, scaleTime } from "d3-scale";
import { area, curveMonotoneX, line } from "d3-shape";
import { pct, toDate, type Dashboard, type ModelForecast } from "../data";
import { useWidth } from "../useWidth";

const M = { top: 26, right: 58, bottom: 28, left: 34 };

/**
 * Hero chart, built up in layers: the normal range for this time of year,
 * last season, this season's reported weeks, then the 4-week forecast with the
 * chance of crossing the surge line on each week.
 */
type Props = {
  data: Dashboard;
  height?: number;
  animKey: string;
  pick?: ModelForecast | null;     // show one model's forecast instead of the main one
  actual?: number[] | null;        // what happened next (case study)
};

export function ForecastChart({ data, height = 340, animKey, pick, actual }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const reduce = useReducedMotion();
  const [hover, setHover] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const { lines, layers, stats } = data;
  const forecast = pick ? { ...pick, dates: data.forecast.dates } : data.forecast;
  const now = { ...data.now, chance: pick ? pick.chance : data.now.chance };
  const fanKey = `${animKey}-${pick?.id ?? "main"}`;
  // The full staged entrance plays on load; switching models later swaps the fan quickly
  const entering = useRef(true);
  useEffect(() => {
    entering.current = true;
    const t = setTimeout(() => { entering.current = false; }, 2600);
    return () => clearTimeout(t);
  }, [animKey]);

  const obs = data.recent.map((d) => ({ date: toDate(d.date), v: d.v }));
  const origin = obs[obs.length - 1];
  const fc = forecast.dates.map((d, i) => ({
    date: toDate(d), p5: forecast.p5[i], p25: forecast.p25[i], p50: forecast.p50[i], p75: forecast.p75[i], p95: forecast.p95[i],
  }));
  const fan = [{ date: origin.date, p5: origin.v, p25: origin.v, p50: origin.v, p75: origin.v, p95: origin.v }, ...fc];
  const lay = layers.filter((l) => l.lo !== null).map((l) => ({ ...l, date: toDate(l.date) }));
  const last = layers.filter((l) => l.last !== null).map((l) => ({ date: toDate(l.date), v: l.last! }));

  const innerW = Math.max(width - M.left - M.right, 10);
  const innerH = height - M.top - M.bottom;
  // Scale to what's happening now (reported, normal range, 50% forecast range). When the
  // surge line is far above, it's marked at the top instead of flattening everything.
  const dataMax = Math.max(...obs.map((d) => d.v), ...forecast.p75, ...lay.map((l) => l.hi ?? 0), ...(actual ?? [])) * 1.35;
  const surgeOnChart = lines.surge <= dataMax * 1.6;
  const yMax = surgeOnChart ? Math.max(dataMax, lines.surge * 1.15) : dataMax;
  const x = scaleTime().domain([obs[0].date, fc[fc.length - 1].date]).range([0, innerW]);
  const y = scaleLinear().domain([0, yMax]).range([innerH, 0]).nice().clamp(true);

  type F = (typeof fan)[number];
  type L = (typeof lay)[number];
  type P = { date: Date; v: number };
  const curve = curveMonotoneX;
  const normal = area<L>().x((d) => x(d.date)).y0((d) => y(d.lo!)).y1((d) => y(d.hi!)).curve(curve)(lay) ?? "";
  const lastLine = line<P>().x((d) => x(d.date)).y((d) => y(d.v)).curve(curve)(last) ?? "";
  const obsLine = line<P>().x((d) => x(d.date)).y((d) => y(d.v)).curve(curve)(obs) ?? "";
  const outer = area<F>().x((d) => x(d.date)).y0((d) => y(d.p5)).y1((d) => y(d.p95)).curve(curve)(fan) ?? "";
  const inner = area<F>().x((d) => x(d.date)).y0((d) => y(d.p25)).y1((d) => y(d.p75)).curve(curve)(fan) ?? "";
  const median = line<F>().x((d) => x(d.date)).y((d) => y(d.p50)).curve(curve)(fan) ?? "";

  const s = (t: number) => (reduce ? 0 : t);
  const fanStart = x(origin.date);
  const lastFc = fc[fc.length - 1];

  // Hover: nearest week
  type HoverPoint = { date: Date; v: number; kind: string; normal?: number | null; lo?: number; hi?: number; chance?: number };
  const pts: HoverPoint[] = [
    ...obs.map((p) => ({ date: p.date, v: p.v, kind: "Reported", normal: layers.find((l) => toDate(l.date).getTime() === p.date.getTime())?.mid ?? null })),
    ...fc.map((p, i) => ({ date: p.date, v: p.p50, kind: "Most likely", lo: p.p5, hi: p.p95, chance: now.chance?.[i] })),
  ];
  const onMove = (e: React.PointerEvent) => {
    const box = svgRef.current?.getBoundingClientRect();
    if (!box) return;
    const px = e.clientX - box.left - M.left;
    let best = 0;
    pts.forEach((p, i) => { if (Math.abs(x(p.date) - px) < Math.abs(x(pts[best].date) - px)) best = i; });
    setHover(best);
  };
  const h = hover === null ? null : pts[hover];

  return (
    <div ref={ref} className="relative w-full" style={{ height }}>
      {width > 0 && (
        <svg ref={svgRef} width={width} height={height} role="img" overflow="hidden"
             aria-label="Flu visits per 1,000 for recent weeks, the normal range for this time of year, and the 4-week forecast"
             onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
          <defs>
            <clipPath id={`plot-${animKey}`}><rect x={0} y={0} width={innerW} height={innerH} /></clipPath>
          </defs>
          <g transform={`translate(${M.left},${M.top})`}>
            {y.ticks(4).map((v) => (
              <g key={v}>
                <line x1={0} x2={innerW} y1={y(v)} y2={y(v)} stroke="var(--line)" />
                <text x={-8} y={y(v)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--muted)" className="tabular">{v}</text>
              </g>
            ))}
            {x.ticks(innerW < 420 ? 3 : 6).map((m) => (
              <text key={m.getTime()} x={x(m)} y={innerH + 20} textAnchor="middle" fontSize={11} fill="var(--muted)">
                {m.toLocaleDateString("en-US", { month: "short" })}
              </text>
            ))}

            {/* Surge line, or a marker that it sits above the chart */}
            {surgeOnChart ? (
              <>
                <rect x={0} width={innerW} y={0} height={Math.max(y(lines.surge), 0)} fill="var(--surge)" opacity={0.05} />
                <line x1={0} x2={innerW} y1={y(lines.surge)} y2={y(lines.surge)} stroke="var(--surge)" strokeDasharray="5 4" strokeWidth={1.5} />
                <text x={innerW + 6} y={y(lines.surge)} dy="0.32em" fontSize={11} fontWeight={600} fill="var(--surge)">Surge</text>
              </>
            ) : (
              <text x={innerW + 6} y={4} fontSize={11} fontWeight={600} fill="var(--surge)">
                <tspan x={innerW + 6}>Surge</tspan><tspan x={innerW + 6} dy={13}>{lines.surge.toFixed(1)}</tspan><tspan x={innerW + 6} dy={13}>above</tspan>
              </text>
            )}

            <g clipPath={`url(#plot-${animKey})`}>
              {/* Layer 1: normal range for this time of year */}
              <motion.path key={`normal-${animKey}`} d={normal} fill="var(--normal)"
                           initial={{ opacity: reduce ? 1 : 0 }} animate={{ opacity: 1 }} transition={{ duration: s(0.6) }} />
              {/* Layer 2: last season */}
              <motion.path key={`last-${animKey}`} d={lastLine} fill="none" stroke="var(--muted)" strokeWidth={1.5}
                           strokeDasharray="2 4" strokeLinecap="round"
                           initial={{ opacity: reduce ? 0.8 : 0 }} animate={{ opacity: 0.8 }} transition={{ delay: s(0.3), duration: s(0.6) }} />
              {/* Layer 4: forecast fan, grows out of today */}
              <motion.g key={`fan-${fanKey}`} initial={reduce ? false : { opacity: 0, scaleX: 0 }} animate={{ opacity: 1, scaleX: 1 }}
                        style={{ originX: 0, transformBox: "fill-box" }}
                        transition={{ delay: entering.current ? s(1.5) : 0, duration: s(entering.current ? 0.8 : 0.45), ease: [0.16, 1, 0.3, 1] }}>
                <path d={outer} fill="var(--accent-softer)" />
                <path d={inner} fill="var(--accent-soft)" />
                <path d={median} fill="none" stroke="var(--accent)" strokeWidth={2.5} strokeDasharray="6 5" />
              </motion.g>
            </g>

            {/* Today */}
            <line x1={fanStart} x2={fanStart} y1={0} y2={innerH} stroke="var(--muted)" strokeDasharray="2 3" opacity={0.7} />

            {/* Layer 3: this season, drawn in */}
            <motion.path key={`obs-${animKey}`} d={obsLine} fill="none" stroke="var(--accent)" strokeWidth={3.5}
                         strokeLinecap="round" initial={{ pathLength: reduce ? 1 : 0 }} animate={{ pathLength: 1 }}
                         transition={{ delay: s(0.5), duration: s(1), ease: "easeInOut" }} />
            <motion.circle key={`dot-${animKey}`} cx={fanStart} cy={y(origin.v)} r={6} fill="var(--accent)" stroke="var(--surface)" strokeWidth={2}
                           initial={{ scale: reduce ? 1 : 0 }} animate={{ scale: 1 }}
                           transition={{ delay: s(1.45), type: "spring", stiffness: 260, damping: 16 }} />
            {stats.vsNormal !== null && stats.vsNormal >= 1.5 && (
              <motion.text key={`vs-${animKey}`} x={fanStart - 10} y={y(origin.v) - 12} textAnchor="end" fontSize={12} fontWeight={700}
                           fill="var(--accent)" initial={{ opacity: reduce ? 1 : 0 }} animate={{ opacity: 1 }} transition={{ delay: s(1.6) }}>
                {stats.vsNormal}x normal
              </motion.text>
            )}

            {/* Chance of crossing the surge line by the end of the forecast */}
            {now.chance && (
              <motion.text key={`ch-${fanKey}`} x={x(lastFc.date)} y={-12} textAnchor="end" fontSize={11} fontWeight={600}
                           fill="var(--ink)" initial={{ opacity: reduce ? 1 : 0 }} animate={{ opacity: 1 }} transition={{ delay: entering.current ? s(2) : s(0.2) }}>
                Surge chance by {lastFc.date.toLocaleDateString("en-US", { month: "short", day: "numeric" })}:{" "}
                <tspan fontWeight={800} fill={now.chance[now.chance.length - 1] >= 0.5 ? "var(--surge)" : "var(--accent)"}>
                  {pct(now.chance[now.chance.length - 1])}
                </tspan>
              </motion.text>
            )}
            <text x={fanStart - 6} y={12} textAnchor="end" fontSize={11} fontWeight={600} fill="var(--muted)">Today</text>
            <motion.text key={`end-${fanKey}`} x={x(lastFc.date) + 8} y={y(lastFc.p50)} dy="0.32em" fontSize={12} fontWeight={700}
                         fill="var(--accent)" className="tabular" initial={{ opacity: reduce ? 1 : 0 }} animate={{ opacity: 1 }}
                         transition={{ delay: entering.current ? s(2.3) : s(0.3) }}>
              {lastFc.p50.toFixed(1)}
            </motion.text>

            {/* What happened next (case study) */}
            {actual?.map((v, i) => (
              <motion.circle key={`act-${animKey}-${i}`} cx={x(fc[i].date)} cy={y(v)} r={5.5} fill="var(--surface)"
                             stroke="var(--ink)" strokeWidth={2.5}
                             initial={{ opacity: reduce ? 1 : 0, scale: reduce ? 1 : 0.3 }} animate={{ opacity: 1, scale: 1 }}
                             transition={{ delay: reduce ? 0 : i * 0.15, type: "spring", stiffness: 260, damping: 18 }} />
            ))}

            {h && (
              <g pointerEvents="none">
                <line x1={x(h.date)} x2={x(h.date)} y1={0} y2={innerH} stroke="var(--ink)" opacity={0.18} />
                <circle cx={x(h.date)} cy={y(h.v)} r={4} fill="var(--ink)" />
              </g>
            )}
          </g>
        </svg>
      )}
      {h && width > 0 && (
        <div className="pointer-events-none absolute rounded-xl bg-ink px-3 py-2 text-xs text-bg shadow-lg tabular"
             style={{ left: Math.min(Math.max(x(h.date) + M.left - 85, 0), width - 180), top: M.top + 4, width: 180 }}>
          <div className="font-semibold">{h.date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</div>
          <div>{h.kind}: {h.v.toFixed(1)} per 1,000</div>
          {h.normal != null && <div className="opacity-75">Normal for this week: {h.normal.toFixed(1)}</div>}
          {h.lo !== undefined && <div className="opacity-75">Likely {h.lo.toFixed(1)} to {h.hi!.toFixed(1)}</div>}
          {h.chance !== undefined && <div className="opacity-75">Chance of a surge by then: {pct(h.chance)}</div>}
        </div>
      )}
    </div>
  );
}
