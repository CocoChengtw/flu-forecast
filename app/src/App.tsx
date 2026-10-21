import { useEffect, useMemo, useState } from "react";
import { fmtDay, loadDashboard, toDate, viewOf, type DashboardFile } from "./data";
import { Hero } from "./components/Hero";
import { Actions } from "./components/Actions";
import { Seasons } from "./components/Seasons";
import { StateMap } from "./components/StateMap";
import { ModelCheck } from "./components/ModelCheck";
import { Assistant } from "./components/Assistant";

const VIEW_LABEL: Record<string, string> = { case: "Case study", latest: "Latest week" };

function Header({ file, view, onView }: { file: DashboardFile | null; view: string; onView: (v: string) => void }) {
  const keys = file ? Object.keys(file.views) : [];
  return (
    <header className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-8">
      <span className="text-lg font-extrabold tracking-tight">Flu Surge Outlook</span>
      {file && keys.length > 1 && (
        <div role="tablist" aria-label="Which week to show" className="flex gap-1 rounded-full bg-sunken p-1">
          {keys.map((k) => (
            <button key={k} role="tab" aria-selected={k === view} onClick={() => onView(k)}
                    className={`rounded-full px-3.5 py-1.5 text-sm font-semibold whitespace-nowrap transition-colors ${k === view ? "bg-accent text-white" : "text-muted hover:text-ink"}`}>
              {VIEW_LABEL[k] ?? k}
              <span className="hidden sm:inline">: {fmtDay(file.views[k].updated, { month: "short", day: "numeric", year: "numeric" })}</span>
            </button>
          ))}
        </div>
      )}
    </header>
  );
}

/** Explains what the case-study view is, so nobody mistakes it for this week. */
function CaseBanner({ updated, crossing }: { updated: string; crossing: string | null }) {
  return (
    <div className="bg-sky">
      <p className="mx-auto max-w-7xl px-4 py-3 text-sm md:px-8">
        <b>Replaying the week of {fmtDay(updated, { month: "long", day: "numeric", year: "numeric" })}</b>, the decision point
        {crossing ? ` ${Math.round((toDate(crossing).getTime() - toDate(updated).getTime()) / 6048e5)} weeks before that season's surge (${fmtDay(crossing)})` : ""}. The signal, forecast and recommendations
        use only what was known that week; "What happened next" shows the outcome.
      </p>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto grid max-w-7xl animate-pulse gap-8 px-4 pt-12 md:px-8 lg:grid-cols-[5fr_7fr]" aria-label="Loading">
      <div className="space-y-4">
        <div className="h-2 w-full rounded-full bg-sunken" />
        <div className="h-14 w-2/3 rounded-xl bg-sunken" />
        <div className="h-6 w-full rounded-lg bg-sunken" />
        <div className="h-20 w-full rounded-xl bg-sunken" />
      </div>
      <div className="h-[400px] rounded-2xl bg-sunken" />
    </div>
  );
}

function About() {
  return (
    <footer className="mx-auto max-w-7xl px-4 py-14 text-sm text-muted md:px-8">
      <details className="max-w-[70ch]">
        <summary className="cursor-pointer font-semibold text-ink">About this data</summary>
        <div className="mt-3 space-y-3 leading-relaxed">
          <p>The measure is the share of outpatient doctor visits that are flu (ILI+): visits for flu-like illness times the share of flu tests that are positive. Source: CDC FluView, through the Delphi Epidata API.</p>
          <p>The surge line is the level reached in the busiest quarter of weeks over the last 3 seasons. It counts only people who see a doctor, recent weeks can be revised, and local timing can differ from the national picture.</p>
        </div>
      </details>
      <p className="mt-8">UCLA Anderson time series project. Forecasts support planning; they are not medical advice.</p>
    </footer>
  );
}

export default function App() {
  const [file, setFile] = useState<DashboardFile | null>(null);
  const [view, setView] = useState("case");
  const data = useMemo(() => (file ? viewOf(file, view) : null), [file, view]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard().then((f) => { setFile(f); setView(f.defaultView); }).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <>
      <Header file={file} view={view} onView={setView} />
      {data?.mode === "case" && <CaseBanner updated={data.updated} crossing={data.outcome?.crossing ?? null} />}
      {error && (
        <div className="mx-auto max-w-7xl px-4 py-16 md:px-8">
          <h1 className="text-2xl font-bold">The forecast data didn't load</h1>
          <p className="mt-2 text-muted">Run <code className="rounded bg-sunken px-1.5 py-0.5">python app/export_data.py</code>, then reload. ({error})</p>
        </div>
      )}
      {!data && !error && <Skeleton />}
      {data && (
        <main>
          <div key={view}>
            <Hero data={data} />
            <Actions data={data} />
            <StateMap data={data} />
            <Seasons data={data} />
          </div>
          <ModelCheck data={data} />
          <About />
          <Assistant data={data} />
        </main>
      )}
    </>
  );
}
