import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { scaleLinear } from "d3-scale";
import { curveMonotoneX, line } from "d3-shape";
import { fmtDay, type Dashboard } from "../data";
import { useWidth } from "../useWidth";

// Week 0 of a season is the first week of October
const MONTHS: [number, string][] = [[0, "Oct"], [4, "Nov"], [9, "Dec"], [13, "Jan"], [17, "Feb"], [22, "Mar"], [26, "Apr"], [30, "May"]];
const WEEKS = 34;

function SeasonChart({ data }: { data: Dashboard }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const reduce = useReducedMotion();
  const [focus, setFocus] = useState<number | null>(null);
  const height = 320;
  const m = { top: 12, right: 12, bottom: 26, left: 30 };
  const w = Math.max(width - m.left - m.right, 10);
  const h = height - m.top - m.bottom;
  const yMax = Math.max(...data.seasons.flatMap((s) => s.points.map((p) => p[1]))) * 1.05;
  const x = scaleLinear().domain([0, WEEKS]).range([0, w]);
  const y = scaleLinear().domain([0, yMax]).range([h, 0]).nice();
  const path = line<[number, number]>().x((p) => x(p[0])).y((p) => y(p[1])).curve(curveMonotoneX);
  const cur = data.currentSeason;

  const style = (s: number) =>
    s === cur ? { stroke: "var(--accent)", width: 3.5, opacity: 1 }
    : s === cur - 1 ? { stroke: "var(--ink)", width: 2, opacity: 0.75 }
    : { stroke: "var(--past)", width: 1.5, opacity: 1 };

  return (
    <div ref={ref} className="w-full" style={{ height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Flu visits per 1,000 for every season since 2016, October to May">
          <g transform={`translate(${m.left},${m.top})`}>
            {y.ticks(4).map((v) => (
              <g key={v}>
                <line x1={0} x2={w} y1={y(v)} y2={y(v)} stroke="var(--line)" />
                <text x={-8} y={y(v)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--muted)">{v}</text>
              </g>
            ))}
            {MONTHS.map(([wk, label]) => (
              <text key={label} x={x(wk)} y={h + 19} fontSize={11} fill="var(--muted)">{label}</text>
            ))}
            <line x1={0} x2={w} y1={y(data.lines.surge)} y2={y(data.lines.surge)} stroke="var(--surge)" strokeDasharray="5 4" strokeWidth={1.5} />

            {[...data.seasons].sort((a, b) => style(a.season).width - style(b.season).width).map((s, i) => {
              const st = style(s.season);
              const dim = focus !== null && focus !== s.season;
              return (
                <motion.path key={s.season} d={path(s.points) ?? ""} fill="none" stroke={st.stroke}
                             strokeWidth={focus === s.season ? st.width + 1.5 : st.width} strokeLinecap="round"
                             style={{ opacity: dim ? 0.15 : st.opacity, transition: "opacity 0.2s" }}
                             initial={reduce ? false : { pathLength: 0 }} whileInView={{ pathLength: 1 }}
                             viewport={{ once: true, amount: 0.4 }}
                             transition={{ duration: 1.2, delay: i * 0.05, ease: "easeInOut" }}
                             onPointerEnter={() => setFocus(s.season)} onPointerLeave={() => setFocus(null)} />
              );
            })}
            {(() => {
              const s = data.seasons.find((d) => d.season === cur);
              const p = s?.points[s.points.length - 1];
              return p && <circle cx={x(p[0])} cy={y(p[1])} r={5} fill="var(--accent)" stroke="var(--surface)" strokeWidth={2} />;
            })()}
          </g>
        </svg>
      )}
    </div>
  );
}

function SurgeTimeline({ data }: { data: Dashboard }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const reduce = useReducedMotion();
  const rows = data.surges;
  const rowH = 30;
  const m = { top: 4, right: 12, bottom: 26, left: 72 };
  const height = m.top + m.bottom + rows.length * rowH;
  const w = Math.max(width - m.left - m.right, 10);
  const x = scaleLinear().domain([0, WEEKS]).range([0, w]);

  return (
    <div ref={ref} className="w-full" style={{ height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Weeks each past season spent above the surge line">
          <g transform={`translate(${m.left},${m.top})`}>
            {MONTHS.map(([wk, label]) => (
              <g key={label}>
                <line x1={x(wk)} x2={x(wk)} y1={0} y2={rows.length * rowH} stroke="var(--line)" />
                <text x={x(wk)} y={rows.length * rowH + 19} fontSize={11} fill="var(--muted)">{label}</text>
              </g>
            ))}
            {rows.map((r, i) => {
              const cy = i * rowH + rowH / 2;
              return (
                <g key={r.label}>
                  <text x={-10} y={cy} dy="0.32em" textAnchor="end" fontSize={12} fill="var(--muted)" className="tabular">{r.label}</text>
                  {r.startWeek !== null && r.endWeek !== null ? (
                    <motion.rect x={x(r.startWeek)} y={cy - 7} height={14} rx={7}
                                 width={Math.max(x(r.endWeek + 1) - x(r.startWeek), 14)} fill="var(--surge)" opacity={0.28}
                                 style={{ originX: 0, transformBox: "fill-box" }}
                                 initial={reduce ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }}
                                 viewport={{ once: true, amount: 0.5 }}
                                 transition={{ duration: 0.6, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] }}>
                      <title>{`${r.label}: above the surge line ${fmtDay(r.start!)} to ${fmtDay(r.end!)} (${r.weeksAbove} weeks)`}</title>
                    </motion.rect>
                  ) : (
                    <text x={x(r.peakWeek) + 12} y={cy} dy="0.32em" fontSize={11} fill="var(--muted)">never crossed</text>
                  )}
                  <rect x={x(r.peakWeek) - 5} y={cy - 5} width={10} height={10} transform={`rotate(45 ${x(r.peakWeek)} ${cy})`}
                        fill="var(--surge)">
                    <title>{`${r.label}: peaked ${fmtDay(r.peak)} at ${r.peakValue} per 1,000`}</title>
                  </rect>
                </g>
              );
            })}
          </g>
        </svg>
      )}
    </div>
  );
}

export function Seasons({ data }: { data: Dashboard }) {
  const crossed = data.surges.filter((s) => s.startWeek !== null);
  const earliest = crossed.reduce((a, b) => (a.startWeek! < b.startWeek! ? a : b));
  const latest = crossed.reduce((a, b) => (a.startWeek! > b.startWeek! ? a : b));

  const facts = [
    { value: `${crossed.length} of ${data.surges.length}`, label: "recent seasons crossed the surge line" },
    { value: `${fmtDay(earliest.start!)} to ${fmtDay(latest.start!)}`, label: "range of crossing dates" },
    { value: `${data.stats.medianWeeksAbove} weeks`, label: "typical time above the line" },
  ];

  return (
    <section className="bg-sky"><div className="mx-auto max-w-7xl px-4 py-16 md:px-8">
      <h2 className="text-3xl font-bold tracking-tight">How this season compares</h2>
      <dl className="mt-6 grid gap-6 sm:grid-cols-3">
        {facts.map((f) => (
          <div key={f.label}>
            <dt className="sr-only">{f.label}</dt>
            <dd className="text-2xl font-bold tracking-tight tabular">{f.value}</dd>
            <dd className="text-sm text-muted">{f.label}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-10 grid gap-10 lg:grid-cols-[7fr_5fr]">
        <figure className="rounded-2xl bg-surface p-5">
          <figcaption className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span className="font-semibold">Every season since 2016</span>
            <span className="flex items-center gap-1.5 text-muted"><i className="h-[3px] w-4 rounded bg-accent" />This season</span>
            <span className="flex items-center gap-1.5 text-muted"><i className="h-[2px] w-4 rounded bg-ink opacity-75" />Last season</span>
            <span className="flex items-center gap-1.5 text-muted"><i className="h-[2px] w-4 rounded" style={{ background: "var(--past)" }} />Earlier</span>
          </figcaption>
          <SeasonChart data={data} />
        </figure>
        <figure className="rounded-2xl bg-surface p-5">
          <figcaption className="mb-3 text-sm font-semibold">Weeks above the surge line, and each peak</figcaption>
          <SurgeTimeline data={data} />
        </figure>
      </div>
      <p className="mt-6 text-sm text-muted">2020-21 is left out: flu nearly disappeared during COVID.</p>
    </div></section>
  );
}
