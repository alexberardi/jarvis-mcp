FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY jarvis_mcp/ ./jarvis_mcp/

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -e .

ENV JARVIS_MCP_HOST=0.0.0.0
ENV JARVIS_MCP_PORT=7709

EXPOSE ${JARVIS_MCP_PORT}

CMD ["python", "-m", "jarvis_mcp"]
