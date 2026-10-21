# Flu Surge Outlook (dashboard)

A static web page (React + Vite) that reads one data file, plus a small Python
service for the AI assistant.

```
export_data.py       builds public/data.json from data/processed and results/forecasts
insights.py          signal levels, surge history, crossing probabilities
assistant_server.py  POST /api/ask (Claude), and serves dist/ in production
src/                 the page: Hero, Actions, Seasons, ModelCheck, Assistant
src/content.tsx      recommended actions per audience and level (edit copy here)
```

## Run it locally

```bash
python app/export_data.py          # after new data or new model results
cd app && npm install && npm run dev
python app/assistant_server.py     # optional, in a second terminal: AI answers
```

The assistant needs `ANTHROPIC_API_KEY` in the repo's `.env`. Without it, the
suggested questions still get answers written from the page's numbers.

## Two views

- **Case study** (default): the week of `CASE_WEEK` in `insights.py` (Nov 16, 2025), the main
  test season's decision point 4 weeks before the surge. Every model has a forecast there, the
  signal uses an equal-weight pool of all five (not tuned), and "Show what happened next"
  reveals the outcome. Everything else in that view uses only data known that week.
- **Latest week**: the newest data, where only the seasonal baseline has a forecast.

Run `python app/fetch_states.py` after changing `CASE_WEEK`, so the map has state data for it.

## Add a model

Save forecasts with `rolling_forecast(...)` as usual. Re-run `export_data.py`
and the model card switches from "Due" to "Ready". To drive this week's
forecast, also save one origin to `results/forecasts/live/<model>.csv`.

## Deploy (Netlify)

`app/netlify.toml` builds the page and deploys the AI assistant as a Netlify Function at
`/api/ask` (`netlify/functions/ask.mts`, same instructions as `assistant_server.py`).

```bash
cd app
npx netlify-cli login                 # once
npx netlify-cli deploy --build --prod # creates or updates the site
```

Live AI answers need an Anthropic key in the function's environment. Netlify's AI Gateway
provides one automatically when it's enabled on the account (usage billed to Netlify credits);
otherwise set `ANTHROPIC_API_KEY` in Site configuration > Environment variables. Anyone with the
link can use the assistant, so the function is rate-limited to 20 questions a minute per visitor. Without a key, the suggested questions still answer
from the page's numbers.

Re-run `python app/export_data.py` before deploying so `public/data.json` is current.
