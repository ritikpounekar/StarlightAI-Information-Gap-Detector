# StarlightAI

StarlightAI is an AI-assisted information-gap detection prototype for the Shinchan Online Hackathon 2026 **Digital Dark Spot** challenge. It helps people compare information across sources, spot missing decision criteria and conflicting details, and turn uncertainty into a prioritized verification checklist.

## Run locally (no Docker)

Requirements: Python 3.10+ and Node.js 18+.

1. Install backend packages: `python -m pip install -r backend/requirements.txt`
2. Install frontend packages: `cd frontend` then `npm install`
3. From the project root, launch both services: `python run_starlight.py`
4. Open the dashboard URL printed by the launcher (normally <http://127.0.0.1:5173>). API docs are printed too.

The launcher expects the frontend packages to be installed; it does not install dependencies automatically. It uses ports 8000 and 5173 by default and automatically selects a nearby free port if either is already occupied.

## Demo walkthrough

Choose **Load instant demo**, then **Map the information gaps**. The clearly labeled illustrative scholarship sample intentionally includes two different deadlines and exclusive income-proof requirements. The results show direct source excerpts, missing renewal criteria, source conflicts, freshness warnings, and a checkable action list.

## Add your own sources

- Enter a research question and paste one or more source texts.
- Upload text-based PDF, TXT, or Markdown documents (10 MB maximum per file).
- Add a public HTTP(S) page or PDF URL. Redirects and local/private network URLs are rejected.
- Inspect source excerpts, potential gaps, conflict quotes, and freshness signals. Use the evidence tabs to separate direct excerpts from rule-based verification prompts.

## How to interpret results

The current analysis engine uses transparent keyword and pattern checks; it does **not** make generative-AI claims or establish that a requirement is absent from the real world. “Source coverage” measures whether a topic appeared in the provided text, not whether the information is true or complete. A gap is a prompt to verify, not proof of absence. Conflicts are candidate disagreements that should be resolved against the issuing organization. Inferred checklist prompts are labeled and are never presented as sourced facts.

Uploaded content is processed in memory for the request and is not saved by the application. This prototype does not persist research sessions.

## Stack

- FastAPI, Pydantic, Beautiful Soup, and PyMuPDF
- React 18 and Vite
- Local development API proxy; no Docker or hosted AI service required

## Live Demo & Deployment

- **Live demo:** [Add the deployed StarlightAI URL here]
- **Hosting:** Render free web service (FastAPI) and static site (Vite/React); no Docker required.
- **Deploy:** Connect the GitHub repository to Render and use the included `render.yaml` Blueprint. Set `VITE_API_BASE_URL` to the deployed API base URL on the static site. Set `FRONTEND_ORIGIN` on the API service to the frontend origin; multiple comma-separated origins are accepted. The current prototype runs its transparent heuristic engine and does not require external provider credentials.
- **Keep-alive monitor:** Configure an UptimeRobot HTTP(s) monitor to ping the API's `/api/health` endpoint every 5 minutes. Render's free service may otherwise spin down when idle.

The Render Blueprint pins Python 3.12.8 and configures the SPA fallback. The API exposes both `/health` (local launcher compatibility) and `/api/health` (deployment health check). Research streaming is available at `/api/research/stream` as unbuffered server-sent events.

## Tests and production build

- Backend: `cd backend` then `python -m pytest -q` (8 tests)
- Frontend: `cd frontend` then `npm test` (1 test) and `npm run build`
