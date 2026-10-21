import { useState } from "react";
import { ArrowCounterClockwise, TrendDown, TrendUp, ArrowRight } from "@phosphor-icons/react";
import { fmtDay, LEVELS, pct, type Dashboard } from "../data";
import { HEADLINES } from "../content";
import { ForecastChart } from "./ForecastChart";
import { Gauge } from "./Gauge";

export function Hero({ data }: { data: Dashboard }) {
  const [replay, setReplay] = useState(0);
  const { now, forecast, stats } = data;
  const level = LEVELS[now.level];
  const TrendIcon = now.trend === "rising" ? TrendUp : now.trend === "falling" ? TrendDown : ArrowRight;
  const early = stats.vsNormal !== null && stats.vsNormal >= 1.5;
  const chance4 = now.chance?.[now.chance.length - 1];

  const headline =
    now.level === 1 && early && chance4 !== undefined
      ? `Flu season is starting early. The forecast puts a surge in the next 4 weeks at ${pct(chance4)}.`
      : HEADLINES[now.level];

  const figures = [
    { value: now.value.toFixed(1), unit: "", label: `flu visits per 1,000 doctor visits, ${now.trend}`, icon: TrendIcon },
    stats.vsNormal !== null
      ? { value: `${stats.vsNormal}x`, unit: "", label: `the normal level for early ${fmtDay(data.updated, { month: "long" })}` }
      : { value: fmtDay(data.typicalCrossing), unit: "", label: "typical surge start" },
    stats.leadMin !== null
      ? { value: `${stats.leadMin} to ${stats.leadMax}`, unit: "wks", label: "from this level to a surge, in past seasons" }
      : { value: `${stats.medianWeeksAbove}`, unit: "wks", label: "typical surge length" },
  ];

  return (
    <section className="mx-auto grid max-w-7xl gap-10 px-4 pt-6 pb-16 md:px-8 lg:grid-cols-[5fr_7fr] lg:gap-12 lg:pt-10">
      <div className="flex flex-col">
        <Gauge data={data} />
        <h1 className="mt-4 text-5xl font-extrabold tracking-tight md:text-6xl" style={{ color: `color-mix(in srgb, ${level.color} 85%, black)` }}>
          {level.name}
        </h1>
        <p className="mt-3 max-w-[36ch] text-xl font-medium leading-snug">{headline}</p>

        <dl className="mt-8 grid grid-cols-3 gap-4 border-t border-line pt-6">
          {figures.map((f) => (
            <div key={f.label}>
              <dt className="sr-only">{f.label}</dt>
              <dd className="flex flex-wrap items-baseline gap-x-1 text-2xl font-bold tracking-tight whitespace-nowrap tabular sm:text-3xl">
                {f.value}
                {f.unit && <span className="text-base font-semibold text-muted">{f.unit}</span>}
                {"icon" in f && f.icon && <f.icon size={22} weight="bold" className="self-center text-accent" aria-hidden />}
              </dd>
              <dd className="mt-1 text-sm leading-snug text-muted">{f.label}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-4 shadow-[0_12px_32px_-18px_rgb(28_99_183/0.35)] md:p-6">
        <div className="mb-1 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold">This season and the next 4 weeks</h2>
            <p className="text-sm text-muted">Flu visits per 1,000 doctor visits</p>
          </div>
          <button onClick={() => setReplay((n) => n + 1)}
                  className="flex shrink-0 items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-sm font-medium text-muted transition-transform hover:text-ink active:scale-[0.97]">
            <ArrowCounterClockwise size={15} weight="bold" aria-hidden /> Replay
          </button>
        </div>
        <ForecastChart data={data} animKey={`hero-${replay}`} height={330} />
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
          <span className="flex items-center gap-1.5"><i className="h-[3px] w-5 rounded bg-accent" />This season</span>
          <span className="flex items-center gap-1.5"><i className="h-3 w-5 rounded-sm" style={{ background: "var(--normal)" }} />Normal range</span>
          <span className="flex items-center gap-1.5"><i className="h-0 w-5 border-t-2 border-dotted border-muted" />Last season</span>
          <span className="flex items-center gap-1.5"><i className="h-3 w-5 rounded-sm" style={{ background: "var(--accent-soft)" }} />Forecast range</span>
          <span className="flex items-center gap-1.5"><i className="h-0 w-5 border-t-2 border-dashed border-surge" />Surge line ({data.lines.surge})</span>
        </div>
        {now.model === "naive" && forecast.p50[forecast.p50.length - 1] < now.value && (
          <p className="mt-3 rounded-xl bg-sky px-3 py-2 text-sm text-muted">
            This live view uses the seasonal baseline, which copies last year's later timing, so it likely runs low. It warned earliest in both test seasons; see how all five models compare below.
          </p>
        )}
      </div>
    </section>
  );
}
