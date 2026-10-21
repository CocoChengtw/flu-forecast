// AI assistant for the hosted dashboard (Netlify Function at /api/ask).
// Same instructions and numbers as app/assistant_server.py, which serves the
// assistant locally; keep the two in sync.
//
// POST /api/ask  {"question": "...", "history": [...], "view": "case" | "latest"}
//            ->  {"answer": "..."}
// Needs ANTHROPIC_API_KEY in the Netlify site's environment variables.

import Anthropic from "@anthropic-ai/sdk";
import type { Config } from "@netlify/functions";
import data from "../../public/data.json" with { type: "json" };

const MODEL = "claude-opus-5-5";
const MAX_HISTORY = 12;

type Json = Record<string, any>;

function systemPrompt(view: string): string {
  const { views, defaultView, ...shared } = data as Json;
  const d: Json = { ...shared, ...(views[view] ?? views[defaultView]) };
  const fold = d.mainFold;
  const ready = d.models.filter((m: Json) => m.folds[fold]);
  const facts = {
    view: d.mode === "case" ? "case study: a past week replayed, outcome known" : "latest week",
    data_through: d.updated,
    each_model_this_week: d.modelForecasts.map((m: Json) => ({ model: m.name, surge_chance_by_week: m.chance })),
    what_happened_next: d.outcome,
    unit: "flu visits per 1,000 outpatient doctor visits (ILI+ x 10)",
    surge_line: d.lines.surge,
    season_start_line: d.lines.season,
    now: d.now,
    next_4_weeks: d.forecast,
    recent_weeks: d.recent.slice(-8),
    past_surges: d.surges,
    typical_crossing_date_this_season: d.typicalCrossing,
    season_stats: d.stats,
    states_now: d.states?.states ?? null,
    models_with_results: ready.map((m: Json) => ({
      name: m.name, kind: m.kind,
      avg_miss_by_weeks_ahead: m.folds[fold].mae,
      surge_call_brier: m.folds[fold].brier,
      crps: m.folds[fold].crps,
      coverage_90: m.folds[fold].coverage,
      warning_weeks: m.folds[fold].warningWeeks,
    })),
    models_pending: d.models.filter((m: Json) => !m.folds[fold]).map((m: Json) => m.name),
  };
  return `You explain a U.S. flu early-warning dashboard to hospital managers, public-health staff,
clinic and pharmacy managers. They are not statisticians.

How the dashboard works:
- The measure is ILI+: the share of doctor visits for flu-like illness times the share of flu tests
  that are positive. It is shown as flu visits per 1,000 doctor visits.
- Signal levels: Quiet (summer levels), Elevated (season started, under 50% chance of crossing the
  surge line within 4 weeks), Surge watch (50% or more), Surge (above the surge line).
- The surge line is the 75th percentile of in-season weeks over the last 3 seasons.
- Forecasts are 500 simulated paths per week; "likely range" is the 5th to 95th percentile.
- Two views: the case study (a past week, every model has a forecast, the signal uses an
  equal-weight pool of all five, outcome known) and the latest week, whose forecast comes from the
  seasonal baseline (same week last year plus past misses), which can lag a season that starts
  earlier than last year. ETS, ARIMA, Prophet and Chronos have backtest
  results (models_with_results): the most accurate models follow momentum and warn late, while the
  seasonal baseline and Prophet warn of surges weeks earlier. Chronos's ranges are too narrow.
- 2020-21 is excluded because flu nearly disappeared during COVID.
- season_stats: vsNormal = this week vs the median of past seasons at the same week; leadMin/leadMax =
  weeks from today's level to a surge crossing in past seasons; medianWeeksAbove = typical surge length.
- The page gives actions for hospitals, public health, clinics and pharmacies, and individuals.

Dashboard numbers (JSON):
${JSON.stringify(facts)}

Answer rules:
- Use only these numbers. If the answer is not in them, say so plainly.
- Plain words, short sentences, at most 90 words. No headings, no tables, no em dashes.
- Use "per 1,000 visits" for values and whole percentages for chances.
- You may suggest practical actions, but do not give individual medical advice.`;
}

const reply = (status: number, body: Json) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

let client: Anthropic | null = null;   // created on first use, so a missing key is a clean 503

export default async (req: Request): Promise<Response> => {
  if (req.method !== "POST") return reply(405, { error: "Use POST." });

  let body: Json;
  try {
    body = await req.json();
  } catch {
    return reply(400, { error: "The request was not valid JSON." });
  }
  const question = String(body.question ?? "").trim().slice(0, 2000);
  if (!question) return reply(400, { error: "Ask a question first." });

  const history: Anthropic.Beta.BetaMessageParam[] = (Array.isArray(body.history) ? body.history : [])
    .slice(-MAX_HISTORY)
    .filter((h: Json) => h?.role === "user" || h?.role === "assistant")
    .map((h: Json) => ({ role: h.role, content: String(h.content ?? "").slice(0, 2000) }));
  while (history.length && history[0].role !== "user") history.shift();
  const messages: Anthropic.Beta.BetaMessageParam[] = [...history, { role: "user", content: question }];

  if (!process.env.ANTHROPIC_API_KEY) {
    return reply(503, { error: "The assistant is not set up yet. Add ANTHROPIC_API_KEY in Netlify." });
  }
  client ??= new Anthropic();

  try {
    const response = await client.beta.messages.create({
      model: MODEL,
      max_tokens: 2000,
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",                    // retry declined requests on Anthropic's recommended model
      output_config: { effort: "low" },        // short factual answers
      system: [{ type: "text", text: systemPrompt(String(body.view ?? "")), cache_control: { type: "ephemeral" } }],
      messages,
    });
    if (response.stop_reason === "refusal") {
      return reply(200, { answer: "I can't help with that one. Try asking about the forecast, the levels or past seasons." });
    }
    const answer = response.content.map((b) => (b.type === "text" ? b.text : "")).join("").trim();
    return reply(200, { answer });
  } catch (err) {
    if (err instanceof Anthropic.AuthenticationError) return reply(503, { error: "The assistant has no valid API key." });
    if (err instanceof Anthropic.RateLimitError) return reply(429, { error: "The assistant is busy. Try again in a minute." });
    if (err instanceof Anthropic.APIConnectionError) return reply(503, { error: "The assistant can't reach the AI service right now." });
    if (err instanceof Anthropic.APIError) return reply(502, { error: `The AI service returned an error (${err.status}).` });
    throw err;
  }
};

export const config: Config = { path: "/api/ask" };
