# LangGraph agent that generates and explain plots

## Installation

```terminal
uv sync
```

The project needs a `.env` file with the following environment variables:

```text
DATABASE_URL
GOOGLE_API_KEY
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
LANGFUSE_HOST
```

- `DATABASE_URL`: relative or absolute to the database file (absolute path can be obtained via `realpath data/database.db`)
- `GOOGLE_API_KEY`: obtained from `https://aistudio.google.com/app/api-keys`. Log in and generate a new key
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST`: can be obtained on [Langfuse](https://langfuse.com/docs/observability/get-started#get-api-keys). They are optional, leave empty if tracing is not needed.

There's a sample `.env.template` file to be used as base for the `.env` file.

## Run self-hosted Langfuse with docker (optional)

```terminal
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up
```

[Langfuse docs](https://langfuse.com/self-hosting/deployment/docker-compose)

## Run

Run `streamlit run ui.py --server.headless true` then go to `http://localhost:8501/` in a browser.

## Demo

TBA
