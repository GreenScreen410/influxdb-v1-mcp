FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY . /app

RUN uv sync

EXPOSE 9003

CMD ["uv", "run", "src/server.py", "--host", "0.0.0.0", "--transport", "sse"]