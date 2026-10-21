import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { CheckCircle, Flask, XCircle } from "@phosphor-icons/react";
import { fmtDay, pct, type Dashboard, type Model } from "../data";
import { SeasonReplay } from "./SeasonReplay";

function SampleTag() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[#e9cf8f] bg-[#fdf6e7] px-2 py-0.5 text-[11px] font-semibold text-[#7a5604]">
      <Flask size={11} weight="bold" aria-hidden /> Sample
    </span>
  );
}

/** One row per model, ranked by CRPS (the team's main score in src/compare.py). Bars have no track on purpose. */
function Comparison({ models, fold }: { models: Model[]; fold: string }) {
  const reduce = useReducedMotion();
  const base = models.find((m) => m.id === "naive")?.folds[fold];
  const rows = models.filter((m) => m.folds[fold]?.crps != null)
    .sort((x, y) => x.folds[fold]!.crps! - y.folds[fold]!.crps!);
  if (!rows.length) return null;
  const f = (m: Model) => m.folds[fold]!;
  const maxCrps = Math.max(...rows.map((m) => f(m).crps!));
  const best = rows[0];
  const maxWarn = Math.max(...rows.map((m) => f(m).warningWeeks));
  const earliestAll = rows.filter((m) => f(m).warningWeeks === maxWarn);   // ties are common with ~4 events
  const bestCall = rows.reduce((x, y) => ((f(y).brier ?? 1) < (f(x).brier ?? 1) ? y : x));
  const skill = (m: Model) => (base ? Math.round((1 - f(m).crps! / base.crps!) * 100) : 0);
  const crossing = f(rows[0]).crossing;

  const findings: { label: string; model: Model; names?: string; note: string }[] = [
    { label: "Most accurate overall", model: best, note: `${skill(best)}% better than the baseline` },
    { label: "Best surge calls", model: bestCall, note: `surge-call score ${f(bestCall).brier?.toFixed(3)}` },
    { label: "Earliest warning", model: earliestAll[0], names: earliestAll.map((m) => m.name).join(", "),
      note: maxWarn ? `${maxWarn} weeks before the surge` : "No model gave 50% before the surge" },
  ];

  return (
    <div className="mt-14">
      <h3 className="text-xl font-bold tracking-tight">How the models compare, {fold} season</h3>
      <dl className="mt-5 grid gap-4 sm:grid-cols-3">
        {findings.map((x) => (
          <div key={x.label} className="rounded-2xl bg-sky p-4">
            <dt className="text-sm text-muted">{x.label}</dt>
            <dd className="mt-1 text-xl font-bold">{x.names ?? x.model.name}{!x.names && x.model.sample && <span className="ml-2 align-middle"><SampleTag /></span>}</dd>
            <dd className="text-sm text-muted">{x.note}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-muted">
            <tr className="border-b border-line">
              <th className="py-2 pr-4 pl-2 font-medium">Model</th>
              <th className="py-2 pr-4 font-medium">Overall score (CRPS)</th>
              <th className="py-2 pr-4 font-medium">vs. baseline</th>
              <th className="py-2 pr-4 font-medium">Average miss, 4 weeks ahead</th>
              <th className="py-2 pr-4 font-medium">Surge-call score</th>
              <th className="py-2 pr-4 font-medium">Warning before surge</th>
              <th className="py-2 font-medium">Range hit rate</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m, i) => {
              const b = f(m);
              const sk = skill(m);
              return (
                <tr key={m.id} className={m.id === best.id ? "bg-sky" : ""}>
                  <td className="py-3 pr-4 pl-2">
                    <span className="font-semibold">{m.name}</span>
                    <span className="ml-2 text-xs text-muted">{m.kind}</span>
                    {m.sample && <span className="ml-2 align-middle"><SampleTag /></span>}
                  </td>
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <motion.i className="block h-2.5 rounded-full bg-accent"
                                style={{ width: `${(b.crps! / maxCrps) * 120}px`, originX: 0 }}
                                initial={reduce ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
                                transition={{ delay: i * 0.06, duration: 0.5 }} />
                      <span className="tabular">{b.crps!.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className={`py-3 pr-4 font-semibold tabular ${m.id === "naive" ? "text-muted" : sk > 0 ? "text-quiet" : "text-surge"}`}>
                    {m.id === "naive" ? "Baseline" : `${Math.abs(sk)}% ${sk > 0 ? "better" : "worse"}`}
                  </td>
                  <td className="py-3 pr-4 tabular">{b.mae[3].toFixed(1)}</td>
                  <td className={`py-3 pr-4 tabular ${m.id === bestCall.id ? "font-semibold" : ""}`}>{b.brier?.toFixed(3) ?? "n/a"}</td>
                  <td className={`py-3 pr-4 tabular ${maxWarn && b.warningWeeks === maxWarn ? "font-semibold" : ""}`}>{b.warningWeeks ? `${b.warningWeeks} wks` : "None"}</td>
                  <td className={`py-3 tabular ${b.coverage !== null && b.coverage < 0.75 ? "font-semibold text-surge" : ""}`}>
                    {b.coverage !== null ? pct(b.coverage) : "n/a"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-4 max-w-[85ch] text-sm text-muted">
        Overall score (CRPS) rates the whole forecast range, per 1,000 visits; lower is better. Surge-call score: 0 is
        perfect, 0.25 is a coin flip. Warning: weeks before the {fold} surge{crossing ? ` (${fmtDay(crossing)})` : ""} that
        the model first gave a 50% chance. Range hit rate: how often the actual value fell inside the 90% range
        (target 90%). Each season has about 4 surge events, so rankings can flip between seasons; compare both.
        {rows.some((m) => m.sample) && " Sample rows are illustrative until the team's results are saved."}
      </p>
    </div>
  );
}

export function ModelCheck({ data }: { data: Dashboard }) {
  const folds = Object.keys(data.models[0].folds);
  const [fold, setFold] = useState(data.mainFold);
  const ready = data.models.filter((m) => m.folds[fold]);
  const [modelId, setModelId] = useState(ready[0]?.id ?? data.models[0].id);
  const model = ready.find((m) => m.id === modelId) ?? ready[0];
  const bt = model?.folds[fold] ?? null;
  const [idx, setIdx] = useState(8);
  const i = bt ? Math.min(idx, bt.origins.length - 1) : 0;
  const o = bt?.origins[i];

  const stat = (label: string, value: string, unit?: string) => (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="text-3xl font-bold tracking-tight tabular">
        {value}{unit && <span className="ml-1 text-sm font-medium text-muted">{unit}</span>}
      </dd>
    </div>
  );

  return (
    <section>
      <div className="mx-auto max-w-7xl px-4 py-16 md:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">How reliable is the forecast?</h2>
            <p className="mt-2 max-w-[60ch] text-muted">Each model replayed past seasons week by week, using only the data it would have had.</p>
          </div>
          <div role="tablist" aria-label="Test season" className="flex gap-1 rounded-full bg-sunken p-1">
            {folds.map((f) => (
              <button key={f} role="tab" aria-selected={f === fold} onClick={() => setFold(f)}
                      className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${f === fold ? "bg-accent text-white" : "text-muted hover:text-ink"}`}>
                {f} season
              </button>
            ))}
          </div>
        </div>

        <ul className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-5">
          {data.models.map((m) => {
            const f = m.folds[fold];
            const selected = model?.id === m.id;
            return (
              <li key={m.id} className="bg-surface">
                <button disabled={!f} onClick={() => setModelId(m.id)} aria-pressed={selected}
                        className={`h-full w-full p-4 text-left transition-colors ${selected ? "bg-sky" : f ? "hover:bg-sky" : "cursor-default"}`}>
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-muted">{m.kind}</span>
                    {m.sample && <SampleTag />}
                  </span>
                  <span className="mt-0.5 block font-semibold">{m.name}</span>
                  <span className="mt-0.5 block text-sm text-muted">{m.about}</span>
                  {f && (
                    <span className="mt-3 block text-sm">
                      <b className="text-lg tabular">{f.mae[3].toFixed(1)}</b>
                      <span className="text-muted"> avg miss, 4 wks</span>
                    </span>
                  )}
                  <span className={`mt-1 block text-xs font-semibold ${selected ? "text-accent" : "text-muted"}`}>
                    {selected ? "Showing below" : m.sample ? `Real results Tue 10/20, ${m.owner}` : "Select to replay"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        {bt && o && model ? (
          <div className="mt-10 grid gap-10 lg:grid-cols-[8fr_4fr]">
            <div>
              <label htmlFor="origin" className="flex items-baseline justify-between gap-4 text-sm">
                <span className="font-semibold">
                  {model.name}: forecast made the week of {fmtDay(o.origin, { month: "long", day: "numeric", year: "numeric" })}
                </span>
                <span className="shrink-0 text-muted">Drag to replay</span>
              </label>
              <input id="origin" type="range" min={0} max={bt.origins.length - 1} value={i}
                     onChange={(e) => setIdx(Number(e.target.value))} className="mt-2 w-full" />
              <SeasonReplay weekly={data.weekly} start={bt.origins[0].origin} end={bt.origins[bt.origins.length - 1].origin}
                            origin={o} surge={data.lines.surge} height={300} />
              <p className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                {o.chance === null ? (
                  <span className="text-muted">Flu was already above the surge line that week.</span>
                ) : (
                  <>
                    {(o.chance >= 0.5) === o.crossed
                      ? <CheckCircle size={18} weight="fill" className="text-quiet" aria-hidden />
                      : <XCircle size={18} weight="fill" className="text-surge" aria-hidden />}
                    <span>Gave a <b className="tabular">{pct(o.chance)}</b> chance of a surge within 4 weeks. Flu <b>{o.crossed ? "did" : "did not"}</b> cross.</span>
                  </>
                )}
                <span className="ml-auto flex items-center gap-3 text-xs text-muted">
                  <span className="flex items-center gap-1.5"><i className="h-[3px] w-4 rounded bg-accent" />Known then</span>
                  <span className="flex items-center gap-1.5"><i className="size-2.5 rounded-full border-2 border-ink" />Next 4 weeks, actual</span>
                </span>
              </p>
            </div>

            <dl className="grid content-start grid-cols-2 gap-x-6 gap-y-7">
              {stat("Average miss, 1 week ahead", bt.mae[0].toFixed(1), "per 1,000")}
              {stat("Average miss, 4 weeks ahead", bt.mae[3].toFixed(1), "per 1,000")}
              {stat("Surge-call score", bt.brier?.toFixed(3) ?? "n/a")}
              {stat("Warning before the surge", bt.warningWeeks ? `${bt.warningWeeks} wks` : "None")}
              {stat("Actual inside the 90% range", bt.coverage !== null ? pct(bt.coverage) : "n/a")}
              {model.sample && (
                <p className="col-span-2 rounded-xl bg-[#fdf6e7] px-3 py-2 text-sm text-[#7a5604]">
                  Sample results for illustration. Real {model.name} results replace them once saved.
                </p>
              )}
            </dl>
          </div>
        ) : (
          <p className="mt-10 rounded-2xl bg-sky p-6 text-muted">No results saved for this season yet. Run a model through src/evaluate.py, then re-run app/export_data.py.</p>
        )}

        <Comparison models={data.models} fold={fold} />
      </div>
    </section>
  );
}
