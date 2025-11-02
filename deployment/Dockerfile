FROM python:3.12.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y sqlite3 curl && rm -rf /var/lib/apt/lists/*

COPY deployment/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY src/ ./src
COPY ui/ ./ui
COPY baml_client/ ./baml_client
COPY baml_src/ ./baml_src

COPY data/database.db ./data/database.db
COPY tests/data ./tests/data

# Streamlit port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
