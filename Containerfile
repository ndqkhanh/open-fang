# OpenFang v1 container — python:3.11-slim, vendored harness_core, FTS5-ready SQLite.
FROM python:3.11-slim

WORKDIR /app

# Vendored harness_core
COPY harness_core ./harness_core
RUN pip install --no-cache-dir -e ./harness_core

# OpenFang project
COPY pyproject.toml ./pyproject.toml
COPY src ./src
COPY tests ./tests
COPY FANG.md ./FANG.md
RUN pip install --no-cache-dir -e '.[dev]'

# Persistent KB lives under /data (mount a volume here for cross-restart persistence).
RUN mkdir -p /data
ENV OPEN_FANG_DB_PATH=/data/open_fang.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/healthz', timeout=2)" || exit 1

CMD ["uvicorn", "open_fang.app:app", "--host", "0.0.0.0", "--port", "8010"]
