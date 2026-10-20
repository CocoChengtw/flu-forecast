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

## Add a model

Save forecasts with `rolling_forecast(...)` as usual. Re-run `export_data.py`
and the model card switches from "Due" to "Ready". To drive this week's
forecast, also save one origin to `results/forecasts/live/<model>.csv`.

## Deploy

`npm run build`, then run `python assistant_server.py --port 8080` on any host
that runs Python: it serves `dist/` and the API together.
