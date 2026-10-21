import { useMemo } from "react";
import { motion, useReducedMotion } from "motion/react";
import { scaleLinear, scaleTime } from "d3-scale";
import { area, curveMonotoneX, line } from "d3-shape";
import { addWeeks, toDate, type BacktestOrigin } from "../data";
import { useWidth } from "../useWidth";

const M = { top: 14, right: 54, bottom: 28, left: 34 };

type Props = {
  weekly: { date: string; v: number }[];   // every reported week, whole test season
  start: string;                           // first forecast week of the season
  end: string;                             // last forecast week
  origin: BacktestOrigin;                  // the forecast being replayed
  surge: number;
  height?: number;
};

/**
 * Whole test season on a fixed axis. Dragging the slider moves the forecast
 * along the season (the reported line extends, the range glides) instead of
 * redrawing the chart, so it's easy to follow how forecasts changed week by week.
 */
export function SeasonReplay({ weekly, start, end, origin, surge, height = 320 }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const reduce = useReducedMotion();
  const from = addWeeks(start, -4);
  const to = addWeeks(end, 4);
  const season = useMemo(
    () => weekly.filter((w) => w.date >= from && w.date <= to).map((w) => ({ date: toDate(w.date), v: w.v })),
    [weekly, from, to],
  );

  const innerW = Math.max(width - M.left - M.right, 10);
  const innerH = height - M.top - M.bottom;
  const x = scaleTime().domain([toDate(from), toDate(to)]).range([0, innerW]);
  const yMax = Math.max(surge * 1.3, ...season.map((d) => d.v), ...origin.bands.p75) * 1.08;
  const y = scaleLinear().domain([0, yMax]).range([innerH, 0]).nice().clamp(true);

  const o = toDate(origin.origin);
  const startV = season.find((d) => d.date.getTime() === o.getTime())?.v ?? 0;
  const fan = [0, 1, 2, 3, 4].map((k) => ({
    date: toDate(addWeeks(origin.origin, k)),
    p5: k ? origin.bands.p5[k - 1] : startV, p25: k ? origin.bands.p25[k - 1] : startV,
    p50: k ? origin.bands.p50[k - 1] : startV, p75: k ? origin.bands.p75[k - 1] : startV,
    p95: k ? origin.bands.p95[k - 1] : startV,
  }));
  type F = (typeof fan)[number];
  const curve = curveMonotoneX;
  const seasonLine = line<{ date: Date; v: number }>().x((d) => x(d.date)).y((d) => y(d.v)).curve(curve)(season) ?? "";
  const outer = area<F>().x((d) => x(d.date)).y0((d) => y(d.p5)).y1((d) => y(d.p95)).curve(curve)(fan) ?? "";
  const inner = area<F>().x((d) => x(d.date)).y0((d) => y(d.p25)).y1((d) => y(d.p75)).curve(curve)(fan) ?? "";
  const median = line<F>().x((d) => x(d.date)).y((d) => y(d.p50)).curve(curve)(fan) ?? "";

  // One spring for everything that follows the slider
  const glide = reduce ? { duration: 0 } : { type: "spring" as const, stiffness: 220, damping: 30 };
  const ox = x(o);

  return (
    <div ref={ref} className="w-full" style={{ height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" overflow="hidden"
             aria-label="Reported flu visits for the whole test season, with the forecast made in the chosen week">
          <defs>
            <clipPath id="replay-plot"><rect x={0} y={0} width={innerW} height={innerH} /></clipPath>
            <clipPath id="replay-reported">
              <motion.rect x={0} y={-10} height={innerH + 20} initial={false} animate={{ width: ox }} transition={glide} />
            </clipPath>
          </defs>
          <g transform={`translate(${M.left},${M.top})`}>
            {y.ticks(4).map((v) => (
              <g key={v}>
                <line x1={0} x2={innerW} y1={y(v)} y2={y(v)} stroke="var(--line)" />
                <text x={-8} y={y(v)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--muted)" className="tabular">{v}</text>
              </g>
            ))}
            {x.ticks(innerW < 420 ? 4 : 8).map((m) => (
              <text key={m.getTime()} x={x(m)} y={innerH + 20} textAnchor="middle" fontSize={11} fill="var(--muted)">
                {m.toLocaleDateString("en-US", { month: "short" })}
              </text>
            ))}
            <line x1={0} x2={innerW} y1={y(surge)} y2={y(surge)} stroke="var(--surge)" strokeDasharray="5 4" strokeWidth={1.5} />
            <text x={innerW + 6} y={y(surge)} dy="0.32em" fontSize={11} fontWeight={600} fill="var(--surge)">Surge</text>

            {/* What happened later, faint, so the forecast can be judged against it */}
            <path d={seasonLine} fill="none" stroke="var(--past)" strokeWidth={2} strokeDasharray="3 4" />
            {/* What was known when the forecast was made */}
            <path d={seasonLine} fill="none" stroke="var(--accent)" strokeWidth={3} clipPath="url(#replay-reported)" />

            <g clipPath="url(#replay-plot)">
              <motion.path initial={false} animate={{ d: outer }} transition={glide} fill="var(--accent-softer)" />
              <motion.path initial={false} animate={{ d: inner }} transition={glide} fill="var(--accent-soft)" />
              <motion.path initial={false} animate={{ d: median }} transition={glide} fill="none" stroke="var(--accent)" strokeWidth={2.5} strokeDasharray="6 5" />
            </g>

            <motion.line initial={false} animate={{ x1: ox, x2: ox }} transition={glide} y1={0} y2={innerH}
                         stroke="var(--ink)" strokeDasharray="2 3" opacity={0.5} />
            <motion.circle initial={false} animate={{ cx: ox, cy: y(startV) }} transition={glide} r={5}
                           fill="var(--accent)" stroke="var(--surface)" strokeWidth={2} />
            {origin.actual.map((v, i) => (
              <motion.circle key={i} initial={false} animate={{ cx: x(fan[i + 1].date), cy: y(v) }} transition={glide}
                             r={5} fill="var(--surface)" stroke="var(--ink)" strokeWidth={2} />
            ))}
          </g>
        </svg>
      )}
    </div>
  );
}
