import { useEffect, useState } from "react";
import { fmtDay, loadDashboard, type Dashboard } from "./data";
import { Hero } from "./components/Hero";
import { Actions } from "./components/Actions";
import { Seasons } from "./components/Seasons";
import { StateMap } from "./components/StateMap";
import { ModelCheck } from "./components/ModelCheck";
import { Assistant } from "./components/Assistant";

function Header({ updated }: { updated?: string }) {
  return (
    <header className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:px-8">
      <span className="text-lg font-extrabold tracking-tight">Flu Surge Outlook</span>
      {updated && (
        <span className="text-sm text-muted"><span className="hidden sm:inline">U.S. data through </span>{fmtDay(updated, { month: "short", day: "numeric", year: "numeric" })}</span>
      )}
    </header>
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
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <>
      <Header updated={data?.updated} />
      {error && (
        <div className="mx-auto max-w-7xl px-4 py-16 md:px-8">
          <h1 className="text-2xl font-bold">The forecast data didn't load</h1>
          <p className="mt-2 text-muted">Run <code className="rounded bg-sunken px-1.5 py-0.5">python app/export_data.py</code>, then reload. ({error})</p>
        </div>
      )}
      {!data && !error && <Skeleton />}
      {data && (
        <main>
          <Hero data={data} />
          <Actions data={data} />
          <StateMap data={data} />
          <Seasons data={data} />
          <ModelCheck data={data} />
          <About />
          <Assistant data={data} />
        </main>
      )}
    </>
  );
}
