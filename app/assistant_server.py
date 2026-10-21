"""
AI assistant for the dashboard, plus a static file server for the built page.

POST /api/ask  {"question": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}
           ->  {"answer": "..."}

Claude answers from the numbers in public/data.json only. The API key stays
on this server (ANTHROPIC_API_KEY in the repo's .env), never in the browser.

Development (the Vite dev server forwards /api here):
    python app/assistant_server.py
Production (serves app/dist and the API from one process):
    cd app && npm run build && python assistant_server.py --port 8080
"""

import argparse
import json
import os
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic

APP = Path(__file__).resolve().parent
DATA = APP / "public" / "data.json"
DIST = APP / "dist"
MODEL = "claude-opus-5-5"
MAX_HISTORY = 12                 # earlier turns kept per conversation

try:
    from dotenv import load_dotenv
    load_dotenv(APP.parent / ".env")
except ImportError:
    pass

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Created on first use, so the static site still runs without credentials."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


@lru_cache(maxsize=1)
def system_prompt(data_mtime: float) -> str:
    """Instructions plus a compact copy of the dashboard numbers. Cached per data version."""
    d = json.loads(DATA.read_text())
    ready = [m for m in d["models"] if m["folds"][d["mainFold"]]]
    facts = {
        "data_through": d["updated"],
        "unit": "flu visits per 1,000 outpatient doctor visits (ILI+ x 10)",
        "surge_line": d["lines"]["surge"],
        "season_start_line": d["lines"]["season"],
        "now": d["now"],
        "next_4_weeks": d["forecast"],
        "recent_weeks": d["recent"][-8:],
        "past_surges": d["surges"],
        "typical_crossing_date_this_season": d["typicalCrossing"],
        "season_stats": d["stats"],
        "states_now": (d.get("states") or {}).get("states"),
        "models_with_results": [{"name": m["name"], "kind": m["kind"],
                                 "avg_miss_by_weeks_ahead": m["folds"][d["mainFold"]]["mae"],
                                 "surge_call_brier": m["folds"][d["mainFold"]]["brier"],
                                 "crps": m["folds"][d["mainFold"]]["crps"],
                                 "coverage_90": m["folds"][d["mainFold"]]["coverage"],
                                 "warning_weeks": m["folds"][d["mainFold"]]["warningWeeks"]} for m in ready],
        "models_pending": [m["name"] for m in d["models"] if m not in ready],
    }
    return f"""You explain a U.S. flu early-warning dashboard to hospital managers, public-health staff,
clinic and pharmacy managers. They are not statisticians.

How the dashboard works:
- The measure is ILI+: the share of doctor visits for flu-like illness times the share of flu tests
  that are positive. It is shown as flu visits per 1,000 doctor visits.
- Signal levels: Quiet (summer levels), Elevated (season started, under 50% chance of crossing the
  surge line within 4 weeks), Surge watch (50% or more), Surge (above the surge line).
- The surge line is the 75th percentile of in-season weeks over the last 3 seasons.
- Forecasts are 500 simulated paths per week; "likely range" is the 5th to 95th percentile.
- Today's forecast comes from the seasonal baseline (same week last year plus past misses), which
  can lag a season that starts earlier than last year. ETS, ARIMA, Prophet and Chronos have backtest
  results (models_with_results): the most accurate models follow momentum and warn late, while the
  seasonal baseline and Prophet warn of surges weeks earlier. Chronos's ranges are too narrow.
- 2020-21 is excluded because flu nearly disappeared during COVID.
- season_stats: vsNormal = this week vs the median of past seasons at the same week; leadMin/leadMax =
  weeks from today's level to a surge crossing in past seasons; medianWeeksAbove = typical surge length.
- The page gives actions for hospitals, public health, clinics and pharmacies, and individuals.

Dashboard numbers (JSON):
{json.dumps(facts)}

Answer rules:
- Use only these numbers. If the answer is not in them, say so plainly.
- Plain words, short sentences, at most 90 words. No headings, no tables, no em dashes.
- Use "per 1,000 visits" for values and whole percentages for chances.
- You may suggest practical actions, but do not give individual medical advice."""


def ask(question: str, history: list[dict]) -> str:
    messages = [{"role": h["role"], "content": str(h["content"])[:2000]}
                for h in history[-MAX_HISTORY:] if h.get("role") in ("user", "assistant")]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": question[:2000]})

    response = get_client().beta.messages.create(
        model=MODEL,
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",                       # retry declined requests on Anthropic's recommended model
        output_config={"effort": "low"},           # short factual answers
        system=[{"type": "text", "text": system_prompt(DATA.stat().st_mtime),
                 "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    if response.stop_reason == "refusal":
        return "I can't help with that one. Try asking about the forecast, the levels or past seasons."
    return "".join(b.text for b in response.content if b.type == "text").strip()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def _json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/api/ask":
            return self._json(404, {"error": "Not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            question = str(body.get("question", "")).strip()
            if not question:
                return self._json(400, {"error": "Ask a question first."})
            return self._json(200, {"answer": ask(question, body.get("history", []))})
        except anthropic.AuthenticationError:
            return self._json(503, {"error": "The assistant has no valid API key. Add ANTHROPIC_API_KEY to .env."})
        except anthropic.RateLimitError:
            return self._json(429, {"error": "The assistant is busy. Try again in a minute."})
        except anthropic.APIConnectionError:
            return self._json(503, {"error": "The assistant can't reach the AI service right now."})
        except anthropic.APIStatusError as e:
            return self._json(502, {"error": f"The AI service returned an error ({e.status_code})."})
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "The request was not valid JSON."})
        except (anthropic.AnthropicError, TypeError):   # TypeError: the SDK found no credentials
            return self._json(503, {"error": "The assistant is not set up yet. Add ANTHROPIC_API_KEY to .env."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8787)))
    args = parser.parse_args()
    print(f"Assistant on http://127.0.0.1:{args.port}  (static files from {DIST.name}/ if built)")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
