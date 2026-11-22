# Troy HealthLink Backend

FastAPI server for the chat, RAG and symptom-triage model. Runs as a Docker image on Cloud Run.

## Layout

```
backend/
├── app/                    # everything the server runs (the Docker image copies only this)
│   ├── main.py             # creates the app, mounts the routes, loads the model at startup
│   ├── config.py           # every setting, typed (pydantic-settings), from env vars or app/.env
│   ├── llm.py              # OpenAI clients with one timeout and retry policy
│   ├── store.py            # the one place that reads and writes Firestore (profiles, chats, messages)
│   ├── api/
│   │   ├── deps.py         # Firebase login check, admin check, rate limits
│   │   ├── ws.py           # the chat WebSocket (/ws/chat)
│   │   ├── sessions.py     # list, rename, delete chats; chat history
│   │   ├── profile.py      # profile and the user's own OpenAI key
│   │   └── rag.py          # PDF upload, /rag/ask, /rag/stats
│   ├── chat/analysis.py    # system prompt, RAG context, ML call, analysis prompt
│   ├── retrieval/          # Firestore vector search (retriever), PDF ingestion, prompt templates
│   ├── triage/             # XGBoost model, symptom extraction, EIG, knowledge base, model files
│   ├── prompts/            # every prompt as a .md file
│   └── data/pdf/           # the source PDFs
├── scripts/                # offline tools: generate training data, feature spec, label encoder
├── evals/                  # retrieval, triage and LLM-judged evals with a baseline and thresholds
├── tests/                  # pytest, run in CI and before every deploy
└── test_*.py               # manual benchmarks against a running server (need real credentials)
```

## Run locally

```bash
cd backend
pip install -r requirements-dev.txt
cp app/.env.example app/.env          # fill in OPENAI_API_KEY at least
gcloud auth application-default login # Firestore credentials
cd app && uvicorn main:app --reload
```

Tests: `cd backend && python -m pytest tests/`. The real-Firestore test runs only when Google credentials are available.

## Train the model

```bash
cd backend/app
python triage/model.py
```

Reads `triage/synthetic_data.csv` (made by `scripts/generate_data.py`) and writes `model.joblib`, `feature_spec.json`, `label_encoder.json` and `training_report.json` into `triage/`.
